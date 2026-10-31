resource "aws_s3_bucket" "reports" {
  bucket        = "${var.project_name}-reports-679857345741"
  force_destroy = true

  tags = {
    Environment = "dev"
    ManagedBy   = "Terraform"
    Lab         = "Lab7"
  }
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id
  versioning_configuration {
    status = "Enabled"
  }
}
