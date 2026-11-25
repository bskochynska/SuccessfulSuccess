# The whole connection string lives in Secret Manager, so the database password
# never appears in the Cloud Run configuration or in the repository.
# (The generated value is still in the Terraform state: keep the state in a
# private HCP Terraform workspace.)
resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.project_name}-database-url"

  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }

  depends_on = [google_project_service.secret_manager]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  # asyncpg connects over the Cloud SQL unix socket mounted at /cloudsql.
  secret_data = "postgresql+asyncpg://${google_sql_user.app_user.name}:${urlencode(random_password.db_password.result)}@/${google_sql_database.meetings.name}?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"
}

# Cloud Run service: the same image that runs locally, no Lambda adapter.
resource "google_cloud_run_v2_service" "api" {
  name     = "${var.project_name}-api"
  location = var.gcp_region

  template {
    service_account = google_service_account.cloud_run.email

    containers {
      # The first apply uses a public hello image, because the backend image
      # cannot exist before the registry does. Deploy the real image afterwards
      # (see gcp/README.md); ignore_changes below keeps Terraform from
      # reverting it.
      image = var.backend_image

      # Cloud Run passes this port to the container in the PORT variable.
      ports {
        container_port = 8080
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "APP_TIMEZONE"
        value = var.app_timezone
      }

      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "RUN_MIGRATIONS_ON_START"
        value = "true"
      }

      # Authentication stays on AWS Cognito: the API validates its tokens.
      # With an empty pool id the API refuses every meetings request.
      env {
        name  = "COGNITO_REGION"
        value = var.cognito_region
      }

      env {
        name  = "COGNITO_USER_POOL_ID"
        value = var.cognito_user_pool_id
      }

      env {
        name  = "COGNITO_CLIENT_ID"
        value = var.cognito_client_id
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    # The Cloud SQL instance has a private IP only, so the service needs a path
    # into the VPC: Direct VPC egress on the default network.
    vpc_access {
      network_interfaces {
        network    = "default"
        subnetwork = "default"
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    volumes {
      name = "cloudsql"

      cloud_sql_instance {
        instances = [google_sql_database_instance.postgres.connection_name]
      }
    }

    # Scale to zero: an idle API costs nothing.
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    timeout = "300s"
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [
    google_project_service.cloud_run,
    google_secret_manager_secret_version.database_url,
    google_project_iam_member.cloud_run_secret_accessor,
    google_project_iam_member.cloud_run_cloudsql_client,
  ]
}

# The API checks Cognito tokens itself, so Cloud Run may accept unauthenticated
# calls (the lab allows this only for APIs that verify tokens on their own).
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
