# Generate random suffix for unique database instance name
resource "random_string" "db_suffix" {
  length  = 6
  special = false
  upper   = false
}

# Private IP range for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "${var.project_name}-db-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = "default"

  depends_on = [google_project_service.service_networking]
}

# Private VPC connection for Cloud SQL
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = "default"
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]

  depends_on = [google_project_service.service_networking]
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_name}-db-${random_string.db_suffix.result}"
  database_version = "POSTGRES_16"
  region           = var.gcp_region

  # Use db-f1-micro tier
  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 10

    database_flags {
      name  = "max_connections"
      value = "50"
    }

    # Private IP only, no public IP
    ip_configuration {
      ipv4_enabled    = false
      private_network = "projects/${var.gcp_project_id}/global/networks/default"
      require_ssl     = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = false
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    location_preference {
      zone = "${var.gcp_region}-a"
    }
  }

  deletion_protection = false

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.cloud_sql_admin
  ]
}

# Cloud SQL Database
resource "google_sql_database" "meetings" {
  name     = "meetings"
  instance = google_sql_database_instance.postgres.name
  charset  = "UTF8"
}

# Generate secure random password
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "-_"
}

# Cloud SQL User
resource "google_sql_user" "app_user" {
  name     = "appuser"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
  type     = "BUILT_IN"
}

# Secret Manager: Store the database password
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.project_name}-db-password"

  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }

  depends_on = [google_project_service.secret_manager]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Secret Manager: AWS SES Access Key ID. Terraform only creates the secret with a
# placeholder; set the real value outside Terraform (gcloud secrets versions add)
# so it never lands in the repository or the state.
resource "google_secret_manager_secret" "aws_ses_key_id" {
  secret_id = "${var.project_name}-aws-ses-key-id"

  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }

  depends_on = [google_project_service.secret_manager]
}

resource "google_secret_manager_secret_version" "aws_ses_key_id" {
  secret      = google_secret_manager_secret.aws_ses_key_id.id
  secret_data = "PLACEHOLDER_AWS_SES_KEY_ID"

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Secret Manager: AWS SES Secret Access Key (same approach).
resource "google_secret_manager_secret" "aws_ses_secret_key" {
  secret_id = "${var.project_name}-aws-ses-secret-key"

  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }

  depends_on = [google_project_service.secret_manager]
}

resource "google_secret_manager_secret_version" "aws_ses_secret_key" {
  secret      = google_secret_manager_secret.aws_ses_secret_key.id
  secret_data = "PLACEHOLDER_AWS_SES_SECRET_KEY"

  lifecycle {
    ignore_changes = [secret_data]
  }
}
