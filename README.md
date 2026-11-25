# SuccessfulSuccess — Lab 9: One Project, Two Clouds

## Deployment Guide

### AWS Services (Staying Put)

The following services remain on AWS and are **not** migrated to GCP:

- **Cognito** (`us-east-1`) — User authentication (email + password, Google OAuth)
  - Pool ID: `${COGNITO_USER_POOL_ID}` (from `.env`)
  - Client ID: `${COGNITO_CLIENT_ID}` (from `.env`)
  - Cloud Run validates JWT tokens issued by Cognito via OIDC discovery

- **SES** (`us-east-1`) — Email delivery (infrastructure ready, not yet integrated in v1)
  - Credentials stored in GCP Secret Manager for Cloud Run access
  - Future labs will integrate with Cloud Run

- **Lambda + Bedrock** (`us-east-1`) — AI agenda parsing
  - Agenda parser function: `${AGENDA_PARSER_FUNCTION_URL}` (from terraform outputs)
  - Cloud Run can call the public Lambda URL if needed
  - Full migration to Vertex AI deferred to future lab

### GCP Services (New)

Deployed in **us-central1** via `gcp/` Terraform configuration:

| Service | Purpose | Details |
|---|---|---|
| **Cloud Run v2** | Serverless API | `spry-api` service, min=0/max=100, $0/month (within free tier) |
| **Cloud SQL** | PostgreSQL database | `db-f1-micro`, 10 GB SSD, ~$9.37/month running (~$1.70/month stopped) |
| **Artifact Registry** | Docker registry | `spry-repo` for backend images (0.5 GB free tier) |
| **Secret Manager** | Secrets storage | DB password, AWS SES credentials (6 active secret versions free) |
| **Firebase Hosting** | Frontend CDN | (Optional) Next.js static deployment (free Spark plan) |

---

## Local Setup (for Testing)

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- `gcloud` CLI (for GCP deployment only)

### 1. Build Backend Docker Image

```bash
docker build -t spry-backend:latest ./backend --build-arg INSTALL_DEV=true
```

This removes the Lambda entrypoint and creates a standard HTTP server listening on `PORT` (default 8080).

### 2. Start PostgreSQL

```bash
docker run -d \
  --name spry-db \
  --network spry-local \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=apppass \
  -e POSTGRES_DB=meetings \
  -p 5432:5432 \
  postgres:17-alpine
```

Wait for healthcheck:

```bash
docker exec spry-db pg_isready -U appuser -d meetings
```

### 3. Run Migrations

```bash
docker run --rm \
  --network spry-local \
  -e DATABASE_URL="postgresql+asyncpg://appuser:apppass@spry-db:5432/meetings" \
  -e RUN_MIGRATIONS_ON_START=true \
  spry-backend:latest \
  alembic upgrade head
```

### 4. Start Backend (Cloud Run Configuration)

```bash
docker run -d \
  --name spry-api \
  --network spry-local \
  -p 8080:8080 \
  -e PORT=8080 \
  -e DATABASE_URL="postgresql+asyncpg://appuser:apppass@spry-db:5432/meetings" \
  -e APP_TIMEZONE="Europe/Kyiv" \
  -e CORS_ORIGINS="http://localhost:3000,http://localhost:3001" \
  -e LOG_LEVEL=INFO \
  -e RUN_MIGRATIONS_ON_START=false \
  spry-backend:latest
```

Test health:

```bash
curl http://localhost:8080/health
# Expected: {"status":"ok","database":"ok","version":"1.0.0"}
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:3000`

### 6. Test End-to-End

Frontend will:
1. Load meetings list from `/api/v1/meetings` (displayed via API client in `lib/api.ts`)
2. Show today's meetings (or empty state if none)
3. Allow creating new meetings

Verify API calls:

```bash
curl http://localhost:8080/api/v1/meetings
# Expected: {"items":[],"total":0,...}
```

### 7. Cleanup

```bash
docker stop spry-api spry-db
docker rm spry-api spry-db
docker network rm spry-local
```

---

## GCP Deployment (Cloud Run + Cloud SQL)

### Prerequisites

1. GCP Project with billing enabled
2. `gcloud` CLI configured:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

### 1. Provision Infrastructure

```bash
cd gcp
terraform init -backend=false
terraform apply -var="gcp_project_id=YOUR_PROJECT_ID"
```

Terraform will:
- Enable required APIs
- Create service accounts (least-privilege IAM)
- Provision Cloud SQL (db-f1-micro PostgreSQL)
- Create Cloud Run service placeholder
- Store DB password in Secret Manager

### 2. Build & Push Backend Image

```bash
docker build -t spry-backend:latest ./backend

gcloud auth configure-docker us-central1-docker.pkg.dev

docker tag spry-backend:latest \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/spry-repo/backend:latest

docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/spry-repo/backend:latest
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy spry-api \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/spry-repo/backend:latest \
  --region us-central1 \
  --platform managed \
  --service-account spry-api-runner@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars "PORT=8080,RUN_MIGRATIONS_ON_START=true"
```

Or update via GCP Console.

### 4. Retrieve Deployment Info

```bash
terraform output
gcloud run services describe spry-api --region us-central1
```

### 5. Test API

```bash
CLOUD_RUN_URL=$(gcloud run services describe spry-api --region us-central1 --format='value(status.url)')
curl $CLOUD_RUN_URL/health
```

### 6. Deploy Frontend (Optional)

Deploy Next.js frontend to Firebase Hosting (separate process).

---

## Cloud SQL Management

### Connect Locally (Cloud SQL Proxy)

```bash
cloud-sql-proxy YOUR_PROJECT_ID:us-central1:spry-db-abc123 &
PGPASSWORD=$(gcloud secrets versions access latest --secret="spry-db-password") \
psql -h localhost -U appuser -d meetings
```

### Stop Cloud SQL Instance (Save Costs)

```bash
gcloud sql instances patch spry-db-abc123 --activation-policy=NEVER
```

Restart:

```bash
gcloud sql instances patch spry-db-abc123 --activation-policy=ALWAYS
```

### Monitor Costs

```bash
gcloud compute project-info describe --project=YOUR_PROJECT_ID | grep -A5 BILLING
gcloud billing accounts list
```

---

## Architecture Decision Record

See `docs/adr/0003-gcp-migration-architecture.md` for:
- AWS-to-GCP service mapping (Replace/Keep/Drop decisions)
- Database choice (Cloud SQL vs Firestore vs Aurora)
- Email provider strategy (SES on AWS, credentials in GCP Secret Manager)
- Features deferred to future labs (auth migration, AI, reports)

---

## Troubleshooting

### Cloud Run Can't Connect to Cloud SQL

Check:
```bash
gcloud run services describe spry-api --region us-central1
# Verify CloudSQL socket annotation is present

gcloud sql instances describe spry-db-abc123
# Verify connection name is correct

gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10
```

### Secret Manager Not Accessible

```bash
gcloud secrets versions access latest --secret="spry-db-password"
gcloud secrets get-iam-policy spry-db-password
# Verify spry-api-runner has roles/secretmanager.secretAccessor
```

### Database Unreachable from Cloud Run

```bash
gcloud run logs read spry-api --region us-central1
# Check for connection errors
```

---

## Cost Estimate & Cloud Comparison (Part 3)

All prices are on-demand list prices in USD (`us-east-1` for AWS, `us-central1` for Google Cloud), excluding tax and assuming 730 hours per month.

### 1. Idle Baseline ("Nobody" — 0 active hours/month)

| Piece | AWS (Lab 4, Stage 2) | Google Cloud (Cloud SQL) | Google Cloud (Firestore alt.) |
| :--- | :--- | :--- | :--- |
| **Frontend + CDN + HTTPS** | CloudFront Free plan, WAF included → **$0.00** | Firebase Hosting free plan → **$0.00** | Firebase Hosting free plan → **$0.00** |
| **API** | Lambda, idle → **$0.00** | Cloud Run, scaled to zero → **$0.00** | Cloud Run, scaled to zero → **$0.00** |
| **Database compute** | Aurora, paused → **$0.00** | Cloud SQL `db-f1-micro` running ($0.0105/h × 730h) → **$7.67** *(or **$0.00** if stopped)* | Serverless (within 50k reads / 20k writes daily free tier) → **$0.00** |
| **Database storage** | ~1 GB at $0.10/GB → **$0.10** | 10 GB SSD at $0.17/GB → **$1.70** | < 1 GiB free tier → **$0.00** |
| **Registry, secrets, logs** | ECR / SSM / CloudWatch → **~$0.20** | Artifact Registry / Secret Manager / Logging (free tier) → **$0.00** | Artifact Registry / Secret Manager / Logging (free tier) → **$0.00** |
| **Total (monthly)** | **≈ $0.30 / month** | **≈ $9.37 / month** *(or **≈ $1.70** if DB stopped)* | **≈ $0.00 / month** |

### 2. Traffic Profiles Comparison (Monthly Cost, USD)

Assumptions:
- **Cloud Run & Lambda:** Student/class workloads stay well within the monthly free tiers (2M requests, 180k vCPU-s, 360k GiB-s on GCP; 1M requests, 400k GB-s on AWS) → **$0.00**.
- **AWS Aurora Serverless v2:** 0.5 ACU minimum ($0.12/ACU-h → $0.06/h while active), auto-pauses when idle, plus ~$0.30/month for storage/logs.
- **GCP Cloud SQL (`db-f1-micro`):** $0.0105/h while running + $1.70/month for 10 GB SSD (billed even when stopped).

| Traffic Profile | Active Hours / Month | AWS Total (Aurora Serverless v2 + Lambda) | GCP Total (Cloud SQL `db-f1-micro` always on) | GCP Total (Cloud SQL stopped when idle) | GCP Total (Firestore) | Cheaper Cloud (Relational DB) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Nobody (Idle)** | 0 h | **~$0.30** ($0 compute + $0.10 storage + $0.20 logs) | **~$9.37** ($7.67 compute + $1.70 SSD) | **~$1.70** ($0 compute + $1.70 SSD) | **$0.00** | **AWS** (by ~$9.07, or ~$1.40 if GCP DB stopped) |
| **2. Class demos (10 × 2 h)** | 20 h | **~$1.50** (20h × $0.06 + $0.30 base) | **~$9.37** (runs 730h) | **~$1.91** (20h × $0.0105 + $1.70 SSD) | **$0.00** | **AWS** (by ~$7.87, or ~$0.41 if GCP DB stopped) |
| **3. Office hours (8 h × 22 d)** | 176 h | **~$10.86** (176h × $0.06 + $0.30 base) | **~$9.37** (runs 730h) | **~$3.55** (176h × $0.0105 + $1.70 SSD) | **$0.00** | **GCP** (saves ~$1.49 even if left running 24/7) |
| **4. Busy around the clock** | 730 h | **~$44.10** (730h × $0.06 + $0.30 base) | **~$9.37** (730h × $0.0105 + $1.70 SSD) | **~$9.37** (runs 730h) | **~$0.00–$1.00** | **GCP** (saves ~$34.73/month) |

### 3. Cost Analysis Questions

1. **Which cloud is cheaper for each profile, and which single line decides it?**
   - **Nobody (0 h) & Class demos (20 h/month):** **AWS** is cheaper (~$0.30 and ~$1.50 vs. ~$9.37 on GCP with Cloud SQL running 24/7).
   - **Office hours (176 h/month) & Busy 24/7 (730 h/month):** **GCP** is cheaper (~$9.37 vs. ~$10.86 and ~$44.10 on AWS).
   - **The single line that decides it:** **Database compute** (`Aurora Serverless v2` vs. `Cloud SQL db-f1-micro`). Frontend, API compute, registry, and secrets cost $0 or mere cents on both platforms; the cost crossover happens because Aurora auto-pauses at $0 when idle but charges $0.06/h (0.5 ACU) when active, whereas Cloud SQL has no auto-pause but costs a flat $0.0105/h (~6× cheaper per active hour). *(If Firestore is chosen instead of SQL, GCP wins all four profiles at ~$0/month).*

2. **Where is the equivalent cost trap on the GCP side (compared to Aurora being kept awake on AWS)?**
   - **With Cloud SQL:**
     1. **Forgetting to stop the instance:** Because Cloud SQL does not auto-pause on idle, leaving `db-f1-micro` running during idle periods silently burns **$7.67/month** (or **$25.55/month** if provisioned as `db-g1-small`). Even when stopped, the 10 GB SSD continues billing **$1.70/month** until deleted.
     2. **Disabling Cloud Run scale-to-zero:** Setting `min_instance_count >= 1` allocates continuous CPU and memory billing even with zero traffic.
   - **With Firestore (serverless alternative):** The trap is **unbounded document reads per request** (e.g., fetching an entire collection of 1,000 items without pagination or caching, or reactive listeners re-reading documents on every UI update). Just 51 loads of a 1,000-document list exhausts the 50,000 daily free reads and immediately triggers per-operation billing.

---

## Next Steps

1. ✅ Complete GCP infrastructure (`gcp/` Terraform)
2. ✅ Build backend Docker image (Cloud Run compatible)
3. ✅ Verify local deployment (API + frontend)
4. 🔄 Deploy to Cloud Run (manual push or CI/CD)
5. 🔄 Deploy frontend to Firebase Hosting
6. 🔄 Test cross-cloud integration (GCP API ↔ AWS Cognito)
7. 🔄 Set up monitoring & logging
8. 🔄 Future: Migrate auth to GCP Identity Platform, move AI to Vertex AI

---

## References

- **ADR 0003:** `docs/adr/0003-gcp-migration-architecture.md`
- **GCP README:** `gcp/README.md`
- **Terraform:** `gcp/versions.tf`, `gcp/cloud_sql.tf`, `gcp/cloud_run.tf`
- **Backend Dockerfile:** `backend/Dockerfile` (HTTP server, no Lambda)
- **Project Spec:** `SPEC.md`, `PROJECT.md`

---

## Support

For issues:
1. Check `gcloud run logs read spry-api --region us-central1`
2. Review ADR 0003 for architecture decisions
3. Refer to `gcp/README.md` for deployment details
4. Contact: See `SPEC.md` section 11 (Known gaps & future work)
