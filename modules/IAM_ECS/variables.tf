variable "role_name" {
  default = "ecsTaskExecutionRole"
}
variable "input_bucket_arn" {
  description = "ARN of input S3 bucket"
  type        = string
}

variable "responses_bucket_arn" {
  description = "ARN of responses S3 bucket"
  type        = string
}