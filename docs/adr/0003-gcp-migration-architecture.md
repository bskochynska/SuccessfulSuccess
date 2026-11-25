# ADR 0003: GCP Migration Architecture

**Date:** 2026-11-25  
**Status:** Decided  
**Lab:** Lab 9 — One project, two clouds: Spry on Google Cloud (no-GCP-account route)

---

## Context

The Spry meetings application currently runs on AWS with:
- **Cognito** for user authentication (email + password, Google OAuth)
- **Lambda + Bedrock** for AI-powered agenda parsing
- **S3** for weekly report exports
- **SES** for email delivery (not yet implemented in v1, reserved for future use)
- **Aurora Serverless v2** (PostgreSQL) for persistence

Lab 9 requires migrating the application to Google Cloud Platform (GCP) while keeping certain AWS services in a multicloud setup to minimize refactoring and leverage existing infrastructure investments.

---

## Decision: AWS-to-GCP Service Mapping

| AWS Service | AWS Component | GCP Service | Decision | Rationale |
|---|---|---|---|---|
| Cognito | User authentication (email, Google OAuth) | Cloud Identity / Identity Platform | **Keep on AWS** | User pool and OIDC configuration are already set up. Migrating to GCP Identity Platform would require redesigning the auth flow, updating frontend env vars, and redeploying the app. For a "no-GCP-account route" lab, maintaining auth on AWS avoids blocking the GCP-side deployment. Cognito issuer URL and JWKS remain accessible to Cloud Run over the internet. |
| SES | Transactional email (weekly reports) | Cloud Task + Pub/Sub → Cloud Functions | **Keep on AWS** | Email delivery is optional in v1 and not yet integrated into the codebase. The infrastructure is ready but unused; migrating it to GCP adds complexity without enabling new features. Keeping SES on AWS allows the lab to focus on core compute (Cloud Run) and data (Cloud SQL). Future lab could move email to Mailgun or similar cloud-agnostic provider. |
| Bedrock + Lambda | AI agenda parsing | Vertex AI / Generative AI API | **Keep on AWS** | Bedrock is deeply integrated into the Lambda function (`app.ai.agenda_lambda.py`). The agenda parser is a standalone feature—not on the critical path for the main meetings app. Cloud Run would require porting the Lambda handler to a different runtime and calling Vertex AI instead. Deferring this to a future lab allows us to deliver the core app on GCP quickly. |
| S3 (reports bucket) | Weekly report exports | Cloud Storage | **Drop for now** | Tightly coupled to the Lambda/agenda function that remains on AWS. Keeping the full pipeline (Bedrock → Lambda → S3) on AWS is simpler than splitting it. Future refactoring will move report generation to GCP. |
| RDS Aurora (PostgreSQL) | Relational data store | Cloud SQL (PostgreSQL, db-f1-micro) | **Replace** | Cloud SQL matches the functionality of Aurora at a lower cost for a small app. The db-f1-micro tier ($0.0105/h, about $7.67/month, plus about $1.70/month for 10 GB SSD; list prices, us-central1) is suitable for development and light workloads. It does not pause on idle, unlike Aurora Serverless v2. Database credentials and connection pooling are managed by Google, reducing operational burden. Schema migrations (Alembic) are database-agnostic and will work unchanged. |
| ECR | Container registry | Artifact Registry | **Replace** | Artifact Registry is GCP's native container registry with tighter integration to Cloud Run (no IAM setup required). Multi-region replication and vulnerability scanning are built in. Same base images (python:3.12-slim) and Dockerfiles; no application changes needed. |
| (none) | (none) | Secret Manager | **Add** | Cloud Run requires credentials (DB password) to be injected at runtime. Secret Manager integrates natively with Cloud Run and securely stores the auto-generated Cloud SQL password. Replaces the need for `.env` files or environment variables in the Cloud Run config. |
| (none) | (none) | Cloud Run v2 | **Add** | Replaces the need to self-manage containers on VMs. Serverless compute with autoscaling (min=0) saves costs when idle. Cold starts are acceptable for a low-traffic app. Supports Cloud SQL socket connections and Secret Manager integration out of the box. |
| (none) | (none) | Firebase Hosting | **Add** | Hosts the Next.js frontend with automatic HTTPS, CDN, and instant global deployment. Integrates with Cloud Run for backend routing via rewrites. No separate load balancer or VM needed. |
| S3 + CloudFront + WAF (static frontend) | Frontend hosting | Firebase Hosting | **Replace (not deployed on the no-account route)** | Same row as the Firebase Hosting entry above: CDN and certificate included. Not deployed here because there is no GCP project. |
| EventBridge Scheduler | Weekly report trigger | Cloud Scheduler | **Keep on AWS for now** | Belongs to the report pipeline that stays on AWS (stretch goal). |
| SQS | Report queue | Pub/Sub or Cloud Tasks | **Keep on AWS for now** | Same reason: part of the weekly report pipeline. |
| S3 event → Lambda | Report mailer trigger | Cloud Storage + Eventarc → Cloud Run | **Keep on AWS for now** | Same reason. |
| CloudWatch Logs | Logs | Cloud Logging | **Replace** | Cloud Run writes stdout to Cloud Logging with no setup. |
| IAM roles | Permissions | Service accounts + IAM roles | **Replace** | One account for Terraform, one for the API, no JSON keys. |
| Terraform `aws` provider | IaC | Terraform `google` provider | **Add** | Same HCL, separate state (HCP workspace `spry-gcp`). |

---

## Architecture Questions: Detailed Answers

### Question A: Database Choice

**Problem:** Cloud SQL pricing varies by availability model and instance size. We must balance latency, cost, and complexity.

**Options evaluated:**

1. **Cloud SQL, db-f1-micro, stopped at night (scheduled stop/start)**
   - Cost: compute $0.0105/h only while running (8 h × 22 days ≈ $1.85/month) + 10 GB SSD $1.70/month, billed even while stopped ≈ $3.55/month.
   - Latency: same region as Cloud Run, not measured; the first request after a start waits for the instance to boot (tens of seconds).
   - Complexity: Cloud Scheduler job (3 free per billing account) or a manual `--activation-policy=NEVER/ALWAYS`; API errors while the instance is stopped.
   - **Impact:** Suitable for a development lab or weekend project. Not reliable for production. Lab 9 focuses on deployment velocity, not uptime SLA.

2. **Cloud SQL, db-f1-micro, 24/7 (always on)**
   - Cost: $0.0105/h × 730 h = $7.67 compute + $1.70 storage ≈ $9.40/month, even if nobody uses the app.
   - Latency: same region as Cloud Run, not measured.
   - Complexity: None. Instance always ready.
   - **Impact:** Simplest option. Acceptable cost for a lab or small production app. Recommended.

3. **Firestore (NoSQL)**
   - Cost: $0.03 per 100K reads, $0.09 per 100K writes, with a free quota every day (50,000 reads, 20,000 writes, 1 GiB stored). Student traffic costs $0 and an idle month costs $0.
   - Latency: same region as Cloud Run, not measured.
   - Complexity: **High.** Meetings schema uses PostgreSQL transactions, Alembic migrations, and SQLAlchemy ORM. Porting to Firestore requires rewriting models, repositories, and all queries. Schema migrations become ad-hoc data migrations. Not feasible for Lab 9.

4. **Aurora Serverless v2 (cross-cloud, keep on AWS)**
   - Cost: Aurora 0–1 ACU pauses when idle, about $0.30/month for an idle month (Lab 4). Cross-cloud traffic adds egress charges on the AWS side.
   - Latency: an internet round trip between GCP us-central1 and AWS us-east-1 on every query (tens of ms, not measured), on top of Aurora's resume delay.
   - Complexity: the database must be reachable from the internet or through a VPN; every request crosses clouds. Adds operational overhead and a security surface.
   - **Impact:** Cheapest in money, worst in latency and security. A migration state, not a target architecture.

**Decision:** **Cloud SQL, db-f1-micro, 24/7.**

- Cost: about $9.40/month running, about $1.70/month stopped (storage). Stop it when not in use.
- Latency: database and API in one region.
- Complexity: Zero. Leverages Cloud Run's native SQL socket integration.
- Code refactoring: None. Alembic migrations work on Cloud SQL out of the box; only the connection string changes.

---

### Question B: Email Provider and Secret Storage

**Current state:**
- SES is provisioned in AWS (infra/reports.tf shows the reports bucket; email config is defined but not yet integrated into the v1 app).
- v1 does not send emails; weekly reports and notifications are planned for v2+.

**Decision:** **Keep SES on AWS, store credentials in GCP Secret Manager.**

**Rationale:**
- SES is mature, reliable, and already verified with the AWS account (sender identity confirmed).
- No code in v1 calls SES, so migration complexity is zero.
- GCP alternatives (Cloud Tasks + Cloud Functions → SendGrid, Mailgun, or Google Groups) would require choosing a new provider and rewriting the integration.

**Storage Architecture:**
1. SES access keys (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY for an IAM user scoped to SES) are generated in the AWS console.
2. Keys are stored in GCP Secret Manager:
   - Secret: `spry-aws-ses-key-id`
   - Secret: `spry-aws-ses-secret-key`
   Terraform creates both with a placeholder and `ignore_changes`; the real values are added outside Terraform with `gcloud secrets versions add`, so they never reach the repository.
3. The Cloud Run service account has `secretmanager.secretAccessor`.
4. When email is implemented, the secrets are mounted as environment variables with `secret_key_ref` (no `gcloud` in the image, no startup script). v1 does not send email yet, so this wiring is not added.
5. The preferred long-term option is to drop the long-lived AWS keys and use a provider with a scoped API key (SendGrid or Mailgun) kept in the same Secret Manager.

**Migration path for v2+:**
- Move email to a cloud-agnostic provider (Mailgun, SendGrid, AWS SES as a GCP backend integration).
- Update secrets and app config; no code refactoring of Spry itself.

---

### Question C: Features NOT Moving to GCP in Lab 9

**Features deferred to future labs:**

1. **Cognito / Authentication**
   - **Why:** Already running in AWS. Cloud Run validates JWT access tokens issued by Cognito's OIDC endpoint. Migrating to GCP Identity Platform would require:
     - Recreating the user pool in GCP.
     - Updating frontend env vars (COGNITO_DOMAIN → IDENTITY_PLATFORM_DOMAIN).
     - Modifying the backend OIDC discovery flow.
   - **Lab scope:** Focus on compute/data migration (Cloud Run + Cloud SQL), not identity.
   - **Unblocked:** Frontend can still call the Cognito login URL (hosted by AWS), and the API accepts the JWT from any OIDC issuer (issuer URL is configurable).

2. **AI Agenda Parser (Lambda + Bedrock)**
   - **Why:** Tightly coupled to AWS Bedrock and Lambda runtime.
   - **Code:** `app/ai/agenda_lambda.py`, `app/ai/agenda.py`, `infra/ai.tf` (Lambda configuration).
   - **Migration effort:** Would require:
     - Porting the Lambda handler to a Cloud Run function or Vertex AI Generative AI client.
     - Updating Bedrock API calls to Vertex AI API.
     - Testing the new model endpoints.
   - **Lab scope:** The agenda parser is a bonus feature for v1. Core meetings (list/create/delete) do not depend on it.
   - **Unblocked:** If needed, Cloud Run can call the AWS Lambda URL over the internet (already has a public URL: `aws_lambda_function_url.agenda_parser_url`).

3. **Weekly Reports (S3 + Lambda scheduled task)**
   - **Why:** Depends on the Lambda function (deferred above) and S3 for storage.
   - **Code:** `app/reports/weekly.py`, `infra/reports.tf` (S3 bucket).
   - **Current state:** Infrastructure is defined but no scheduled task (EventBridge rule) exports reports. Not a v1 feature.
   - **Migration path:** Deferring to v2+. When moved, can use Cloud Storage instead of S3 and Cloud Scheduler + Cloud Functions instead of Lambda + EventBridge.

**Summary:**
- **Lab 9 deliverable:** Meetings CRUD API + frontend on GCP (Cloud Run + Cloud SQL + Artifact Registry) + public deployment (Firebase Hosting).
- **Staying on AWS:** Cognito (auth), SES (email infrastructure), Bedrock + Lambda (agenda parsing).
- **Future labs:** Migrate auth to GCP Identity Platform; move Bedrock calls to Vertex AI; move reports to Cloud Storage + Cloud Functions.

---

## Deployment Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          GCP (us-central1)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Firebase Hosting + Cloud CDN                              │  │
│  │ (frontend: Next.js build, rewrite to Cloud Run /api/*) │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Cloud Run v2 (spry-api)                                   │  │
│  │ • min_instance_count = 0                                  │  │
│  │ • Port 8080 (PORT, uvicorn)                               │  │
│  │ • Service account: spry-api-runner                        │  │
│  │ • CloudSQL socket: unix:/cloudsql/PROJECT:us-central1:db │  │
│  │ • Secret: DATABASE_URL (from Secret Manager)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│          │                              │                        │
│          ▼                              ▼                        │
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │ Cloud SQL        │    │ Secret Manager                   │  │
│  │ (PostgreSQL)     │    │ • spry-db-password               │  │
│  │ • db-f1-micro    │    │ • spry-aws-ses-key-id (AWS)      │  │
│  │ • 10 GB SSD      │    │ • spry-aws-ses-secret-key      │  │
│  │ • meetings DB    │    └──────────────────────────────────┘  │
│  │ • appuser        │                                            │
│  └──────────────────┘                                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Artifact Registry                                         │  │
│  │ (Docker repository: spry-repo)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        AWS (us-east-1)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Cognito User Pool (spry-users)                                 │
│  └─ Client: COGNITO_CLIENT_ID                                   │
│  └─ Google OAuth: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET       │
│                                                                   │
│  (Optional) Lambda + Bedrock (agenda parser)                    │
│  └─ Function URL: AGENDA_PARSER_FUNCTION_URL                    │
│                                                                   │
│  (Optional) SES (email provider for v2+)                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

Internet traffic (HTTPS):
- Browser → Firebase Hosting (CDN edge)
- Firebase Hosting rewrites /api/* to Cloud Run
- Cloud Run calls Cognito OIDC endpoint (AWS) to validate JWT
- Cloud Run calls Lambda agenda parser URL (AWS) if needed
- Cloud Run talks to Cloud SQL via private CloudSQL socket (within GCP network)
```

---

## Terraform Configuration

Complete Terraform configuration will be in `gcp/` directory with:
- `versions.tf` — Google provider, terraform required version, no remote backend (for lab).
- `variables.tf` — GCP project, region (default us-central1), resource naming.
- `main.tf` — GCP API enablement, IAM roles.
- `artifact_registry.tf` — Docker repository (spry-repo).
- `cloud_sql.tf` — PostgreSQL instance, database, user, auto-generated password in Secret Manager.
- `secret_manager.tf` — Secrets for DB password, AWS SES keys.
- `cloud_run.tf` — Service container, CloudSQL socket, secret injection.
- `service_accounts.tf` — terraform-deployer (deployment), spry-api-runner (Cloud Run).

---

## Notes

- No VPN or cross-cloud peering is configured in GCP Terraform. Cloud Run can reach AWS services (Cognito, Lambda, SES) over public HTTPS. Latency is ~100–200 ms for inter-cloud traffic; acceptable for a lab.
- Firebase Hosting is optional for Lab 9. If focus is on backend, frontend can be built and deployed manually (`next build` + `gcloud app deploy` or Cloud Run).
- All GCP resources are tagged with `lab=Lab9`, `project=spry` for cost tracking and cleanup.
