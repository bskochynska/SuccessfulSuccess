output "gcp_project_id" {
  value       = var.gcp_project_id
  description = "GCP Project ID"
}

output "gcp_region" {
  value       = var.gcp_region
  description = "GCP Region"
}

output "artifact_registry_repository_url" {
  value       = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.spry.repository_id}"
  description = "Artifact Registry repository URL for Docker images"
}

output "cloud_sql_instance_name" {
  value       = google_sql_database_instance.postgres.name
  description = "Cloud SQL instance name"
}

output "cloud_sql_instance_connection_name" {
  value       = google_sql_database_instance.postgres.connection_name
  description = "Cloud SQL instance connection name for CloudSQL socket"
}

output "cloud_run_service_url" {
  value       = try(google_cloud_run_v2_service.api.uri, "Not yet deployed")
  description = "Cloud Run service public URL"
}

output "cloud_run_service_name" {
  value       = google_cloud_run_v2_service.api.name
  description = "Cloud Run service name"
}

output "secret_manager_db_password_version" {
  value       = google_secret_manager_secret_version.db_password.version
  description = "Secret Manager version of database password"
}

output "service_account_cloud_run" {
  value       = google_service_account.cloud_run.email
  description = "Service account email for Cloud Run"
}

output "service_account_terraform_deployer" {
  value       = google_service_account.terraform_deployer.email
  description = "Service account email for Terraform deployment"
}
