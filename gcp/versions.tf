terraform {
  required_version = ">= 1.9.0"

  # Its own state, separate from infra/ (workspace spry-dev): one plan cannot
  # break both clouds. For `terraform validate` without any login use
  # `terraform init -backend=false`.
  cloud {
    organization = "ooad-skochynska"
    workspaces {
      name = "spry-gcp"
    }
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }

    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
