# GCP Infrastructure for Spry

This directory contains complete Terraform configuration to provision Spry on Google Cloud Platform (GCP) using Cloud Run, Cloud SQL, and Artifact Registry.

## Overview

**Architecture:**
- **Cloud Run v2** — Serverless compute (min_instance_count = 0 for cost optimization)
- **Cloud SQL PostgreSQL** — db-f1-micro instance (10 GB SSD) with private IP
- **Artifact Registry** — Docker repository for backend image
- **Secret Manager** — Database password and AWS SES credentials storage
- **Cognito (AWS)** — User authentication (stays on AWS)
- **SES (AWS)** — Email delivery (stays on AWS, future use)

**Region:** `us-central1` (default, configurable)

## File Structure

```
gcp/
├── versions.tf              # Terraform version, providers (google, google-beta, random)
├── variables.tf             # Input variables (GCP project, region, resource naming)
├── outputs.tf               # Output values (repository URL, Cloud Run URL, etc.)
├── main.tf                  # GCP API enablement, IAM roles, service accounts
├── cloud_sql.tf             # Cloud SQL instance, database, user, Secret Manager
├── cloud_run.tf             # Cloud Run v2 service with CloudSQL integration
├── .terraform.lock.hcl      # Provider lock file (auto-generated)
├── terraform.tfvars         # (Optional) Variable overrides
├── validation_output.txt    # Output of `terraform validate`
└── README.md                # This file
```

## Prerequisites

1. **GCP Project** with billing enabled.
2. **Terraform >= 1.9.0** installed.
3. **gcloud CLI** configured with credentials:
   ```bash
   gcloud auth application-default login
   ```
4. **Docker image built** and pushed to Artifact Registry (or use placeholder image).

## Initialization & Validation

```bash
cd gcp

# Initialize Terraform without logging in to HCP Terraform
# (the real state lives in the HCP workspace "spry-gcp", separate from infra/)
terraform init -backend=false

# Validate configuration
terraform validate

# Plan infrastructure changes
terraform plan -var="gcp_project_id=YOUR_PROJECT_ID"
```

Expected output: "Success! The configuration is valid."

## Variables

### Required

- **`gcp_project_id`** (string) — GCP Project ID (e.g., `my-project-123`).

### Optional

| Variable | Default | Purpose |
|---|---|---|
| `gcp_region` | `us-central1` | GCP region for all resources |
| `project_name` | `spry` | Resource naming prefix and tagging |
| `environment` | `lab9` | Environment label for resources |
| `enable_cloud_run_socket` | `true` | Enable Cloud SQL socket in Cloud Run |

### Example: `terraform.tfvars`

```hcl
gcp_project_id = "my-gcp-project"
gcp_region     = "us-central1"
project_name   = "spry"
environment    = "lab9"
```

Or pass via CLI:

```bash
terraform plan -var="gcp_project_id=my-gcp-project"
```

## Resource Mapping

| Resource | Type | Details |
|---|---|---|
| **Artifact Registry** | Docker repo | `spry-repo` in region `us-central1` |
| **Cloud SQL** | PostgreSQL 16 | `db-f1-micro`, 10 GB SSD, private IP, VPC peering |
| **Cloud SQL Database** | `meetings` | UTF-8 collation, created with instance |
| **Cloud SQL User** | `appuser` | Auto-generated strong password stored in Secret Manager |
| **Secret Manager** | Secrets (3) | `spry-db-password`, `spry-aws-ses-key-id`, `spry-aws-ses-secret-key` |
| **Cloud Run v2** | Service | `spry-api`, min 0 / max 100 instances, CloudSQL socket attached |
| **Service Accounts** | IAM | `spry-terraform-deployer`, `spry-api-runner` |

## Deployment

### Step 1: Create Infrastructure

```bash
terraform apply -var="gcp_project_id=my-gcp-project"
```

Terraform will:
1. Enable required GCP APIs (Cloud Run, Cloud SQL, Artifact Registry, Secret Manager).
2. Create service accounts with least-privilege IAM roles.
3. Provision Cloud SQL instance, database, and user.
4. Store the auto-generated database password in Secret Manager.
5. Store the full `DATABASE_URL` in Secret Manager; Cloud Run reads it through `secret_key_ref`, so the password is not in the service config.
6. Create the Cloud Run service with a public hello image (the real image does not exist before the registry does).

### Step 2: Build & Push Backend Image

```bash
# Build backend image
docker build -t spry-backend:latest ./backend

# Authenticate with Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Tag and push
docker tag spry-backend:latest us-central1-docker.pkg.dev/MY_PROJECT_ID/spry-repo/backend:latest
docker push us-central1-docker.pkg.dev/MY_PROJECT_ID/spry-repo/backend:latest
```

### Step 3: Deploy to Cloud Run

After Terraform applies and the image is pushed:

```bash
gcloud run deploy spry-api \
  --image us-central1-docker.pkg.dev/MY_PROJECT_ID/spry-repo/backend:latest \
  --region us-central1
```

`gcloud run deploy` on an existing service keeps its service account, secret, Cloud SQL connection and VPC settings. Terraform ignores later image changes (`ignore_changes`), so a new `terraform apply` will not revert it.

To use Cognito, pass `-var cognito_user_pool_id=... -var cognito_client_id=...` (from the AWS `infra/` outputs); with an empty pool id the API refuses all meetings requests. Set `-var cors_origins=<frontend origin>` when the frontend is deployed.

### Step 4: Retrieve Outputs

```bash
terraform output

# Example:
# artifact_registry_repository_url = "us-central1-docker.pkg.dev/my-gcp-project/spry-repo"
# cloud_sql_instance_name = "spry-db-abc123"
# cloud_sql_instance_connection_name = "my-gcp-project:us-central1:spry-db-abc123"
# cloud_run_service_url = "https://spry-api-abc123xyz-uc.a.run.app"
```

## Database Connection

### From Cloud Run

Cloud Run container connects via CloudSQL socket:

```python
# app/config.py
DATABASE_URL = f"postgresql+asyncpg://appuser:{db_password}@/meetings?host=/cloudsql/{connection_name}"
```

Example:
```
postgresql+asyncpg://appuser:PASSWORD@/meetings?host=/cloudsql/my-project:us-central1:spry-db-abc123
```

### From Local Development

1. Create Cloud SQL Auth proxy:

   ```bash
   cloud-sql-proxy my-project:us-central1:spry-db-abc123 --local-host 5432 --port 5432
   ```

2. Connect via `localhost`:

   ```bash
   PGPASSWORD=$(gcloud secrets versions access latest --secret="spry-db-password") \
   psql -h localhost -U appuser -d meetings
   ```

## Secrets Management

### Database Password

Auto-generated by Terraform and stored in Secret Manager (`spry-db-password`). Cloud Run reads the full connection string from the secret `spry-database-url` (`secret_key_ref`); nothing secret is in the repository or in the service config.

To manually retrieve:

```bash
gcloud secrets versions access latest --secret="spry-db-password"
```

### AWS SES Credentials

Placeholders are created:
- `spry-aws-ses-key-id`
- `spry-aws-ses-secret-key`

Update with actual AWS credentials when needed:

```bash
gcloud secrets versions add spry-aws-ses-key-id \
  --data-file=- <<< "ACTUAL_AWS_ACCESS_KEY_ID"

gcloud secrets versions add spry-aws-ses-secret-key \
  --data-file=- <<< "ACTUAL_AWS_SECRET_ACCESS_KEY"
```

## IAM Roles

### `spry-terraform-deployer`

Used for deploying infrastructure. Roles:

- `roles/run.admin` — Cloud Run Admin
- `roles/cloudsql.admin` — Cloud SQL Admin
- `roles/artifactregistry.admin` — Artifact Registry Administrator
- `roles/secretmanager.admin` — Secret Manager Admin
- `roles/serviceusage.serviceUsageAdmin` — Service Usage Admin
- `roles/iam.serviceAccountUser` — Service Account User

**Note:** No downloaded JSON keys. On a laptop Terraform uses your own `gcloud auth application-default login`; in CI the next step is Workload Identity Federation (stretch goal).

### `spry-api-runner`

Used by Cloud Run service. Roles:

- `roles/cloudsql.client` — Connect to Cloud SQL
- `roles/secretmanager.secretAccessor` — Read secrets

## Scaling & Costs

### Cloud Run

- **Min instances:** 0 (scales down when idle)
- **Max instances:** 3
- **Estimated cost:** $0–$1/month for light traffic, $5–50/month for moderate traffic.

### Cloud SQL

- **Tier:** db-f1-micro
- **Storage:** 10 GB SSD
- **Cost:** $0.0105/h while running = $7.67/month, plus 10 GB SSD at $0.17/GB = $1.70/month, about **$9.40/month** (list prices, us-central1, 730 h).
- **Stopped instance:** compute is not billed, storage still is: about $1.70/month.
- **Stop:** `gcloud sql instances patch INSTANCE --activation-policy=NEVER`; start with `ALWAYS`.

### Artifact Registry

- **Storage:** ~0.50 per GB/month (one backend image ~300 MB).
- **Bandwidth:** Free within GCP; paid for egress.

**Total for an idle month: about $9.40 with the database running, about $1.70 with it stopped.** See `LAB9_SUBMISSION.md` for the full comparison with AWS.

## Cleanup

### Destroy All Resources

```bash
terraform destroy -var="gcp_project_id=my-gcp-project"
```

**Warning:** This deletes:
- Cloud Run service
- Cloud SQL instance (data is lost)
- Artifact Registry repository
- Secret Manager secrets
- Service accounts

### Selective Deletion

To keep the database but remove other resources, edit `terraform.tfvars` or manually use GCP Console.

## Troubleshooting

### Issue: Terraform fails with "Insufficient replication blocks"

**Cause:** google_secret_manager_secret requires a replication block.

**Solution:** Ensure `replication { user_managed { replicas { ... } } }` is present.

### Issue: Cloud Run can't connect to Cloud SQL

**Cause:** CloudSQL socket not mounted or IAM role missing.

**Solution:**
1. Check `roles/cloudsql.client` is assigned to service account.
2. Verify Cloud Run annotation: `run.googleapis.com/cloudsql-instances`.
3. Check container logs: `gcloud run logs read spry-api --region us-central1`.

### Issue: Secret Manager secret is empty

**Cause:** Secret version not created.

**Solution:** Manually add version:

```bash
gcloud secrets versions add spry-db-password --data-file=- <<< "YOUR_PASSWORD"
```

## Lab 9 Notes

- **Frontend deployment:** Deploy Next.js frontend separately to Firebase Hosting or Cloud Run (different service).
- **Cognito integration:** Keep Cognito on AWS; configure CORS on Cloud Run.
- **Email (SES):** Placeholder only; implement in v2+ with Secret Manager credentials.
- **AI agenda parser:** Deferred to future lab; keep on AWS Lambda for now.

## References

- [GCP Terraform Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run API Reference](https://cloud.google.com/run/docs/reference/rest)
- [Cloud SQL Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance)
- [Secret Manager Terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret)
- [ADR 0003: GCP Migration Architecture](../docs/adr/0003-gcp-migration-architecture.md)
