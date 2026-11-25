variable "gcp_project_id" {
  type        = string
  description = "GCP Project ID"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.gcp_project_id))
    error_message = "GCP Project ID must be 6-30 characters, lowercase letters, numbers, and hyphens."
  }
}

variable "gcp_region" {
  type        = string
  description = "GCP region for all resources"
  default     = "us-central1"
}

variable "project_name" {
  type        = string
  description = "Project name for resource naming and tagging"
  default     = "spry"
}

variable "environment" {
  type        = string
  description = "Environment (dev, staging, prod)"
  default     = "lab9"
}

variable "enable_cloud_run_socket" {
  type        = bool
  description = "Enable Cloud SQL socket in Cloud Run"
  default     = true
}

variable "backend_image" {
  type        = string
  description = "Container image for the first apply; deploy the real backend image afterwards (see README)"
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "app_timezone" {
  type        = string
  description = "Application timezone"
  default     = "Europe/Kyiv"
}

variable "cors_origins" {
  type        = string
  description = "Comma-separated browser origins allowed by the API (the Firebase Hosting URL when deployed)"
  default     = "http://localhost:3000"
}

variable "cognito_region" {
  type        = string
  description = "AWS region of the Cognito user pool that stays on AWS"
  default     = "us-east-1"
}

variable "cognito_user_pool_id" {
  type        = string
  description = "Cognito user pool id (from the AWS infra/ outputs); empty means the API refuses all meetings requests"
  default     = ""
}

variable "cognito_client_id" {
  type        = string
  description = "Cognito app client id (from the AWS infra/ outputs)"
  default     = ""
}
