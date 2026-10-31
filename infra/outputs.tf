output "user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.client.id
}

output "reports_bucket_name" {
  value = aws_s3_bucket.reports.bucket
}

output "agenda_parser_function_url" {
  value = aws_lambda_function_url.agenda_parser_url.function_url
}
