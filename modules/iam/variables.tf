# IAM role name for Lambda
variable "role_name" {
  description = "Name of the IAM role for Lambda"
  type        = string
}

# Optional: list of S3 bucket ARNs to allow access
variable "s3_buckets" {
  description = "List of S3 bucket ARNs the Lambda role can access"
  type        = list(string)
  default     = []
}