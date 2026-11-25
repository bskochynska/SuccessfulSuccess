# Enable required GCP APIs
resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_sql_admin" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secret_manager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firebase" {
  service            = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "service_networking" {
  service            = "servicenetworking.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry Repository
resource "google_artifact_registry_repository" "spry" {
  location      = var.gcp_region
  repository_id = "${var.project_name}-repo"
  description   = "Docker repository for Spry backend"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]

  labels = {
    project     = var.project_name
    environment = var.environment
    lab         = "lab9"
  }
}

# Service Accounts
resource "google_service_account" "terraform_deployer" {
  account_id   = "${var.project_name}-terraform-deployer"
  display_name = "Terraform Deployer for Spry"
  description  = "Service account for Terraform deployment (no downloaded JSON key)"

  depends_on = [google_project_service.compute]
}

resource "google_service_account" "cloud_run" {
  account_id   = "${var.project_name}-api-runner"
  display_name = "Cloud Run Service Account for Spry API"
  description  = "Service account for Cloud Run container execution"

  depends_on = [google_project_service.compute]
}

# IAM: terraform-deployer gets exactly the roles the lab lists (no Owner/Editor).
# The account has no JSON key: on a laptop Terraform uses your own gcloud
# application default credentials, in CI it would use Workload Identity Federation.
resource "google_project_iam_member" "terraform_deployer_cloud_run" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.terraform_deployer.email}"

  depends_on = [google_service_account.terraform_deployer]
}

resource "google_project_iam_member" "terraform_deployer_cloudsql" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.admin"
  member  = "serviceAccount:${google_service_account.terraform_deployer.email}"

  depends_on = [google_service_account.terraform_deployer]
}

resource "google_project_iam_member" "terraform_deployer_artifact_registry" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.admin"
  member  = "serviceAccount:${google_service_account.terraform_deployer.email}"

  depends_on = [google_service_account.terraform_deployer]
}

resource "google_project_iam_member" "terraform_deployer_secret_manager" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.terraform_deployer.email}"

  depends_on = [google_service_account.terraform_deployer]
}

resource "google_project_iam_member" "terraform_deployer_service_accounts" {
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.terraform_deployer.email}"

  depends_on = [google_service_account.terraform_deployer]
}

resource "google_project_iam_member" "terraform_deployer_service_usage" {
  project = var.gcp_project_id
  role    = "roles/serviceusage.serviceUsageAdmin"
  member  = "serviceAccount:${google_service_account.terraform_deployer.email}"

  depends_on = [google_service_account.terraform_deployer]
}

# IAM: Cloud Run service account can access Cloud SQL
resource "google_project_iam_member" "cloud_run_cloudsql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"

  depends_on = [google_service_account.cloud_run]
}

# IAM: Cloud Run service account can access Secret Manager
resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"

  depends_on = [google_service_account.cloud_run]
}
