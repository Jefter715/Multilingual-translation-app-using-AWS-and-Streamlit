variable "image_url" {
  type        = string
  description = "ECR image URL for the ECS container"
}

variable "execution_role_arn" {
  type        = string
  description = "IAM role ARN for ECS task execution"
  default     = ""   # now Terraform won't prompt
}

variable "subnets" {
  type        = list(string)
  description = "Subnets for ECS tasks"
  default     = []  # now Terraform won't prompt
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where ECS will run"
}

variable "container_port" {
  type        = number
  default     = 80
  description = "Port the container listens on"
}

variable "cpu" {
  type    = string
  default = "256"
}

variable "memory" {
  type    = string
  default = "512"
}
variable "input_bucket_name" {
  type        = string
  description = "Name of the input S3 bucket"
}

variable "responses_bucket_name" {
  type        = string
  description = "Name of the responses S3 bucket"
}


variable "aws_region" {
  type        = string
  description = "AWS region where ECS and other resources run"
}

# Optional: if you want to make the API URL configurable
variable "translation_api_url" {
  type        = string
  description = "Full URL for the translation API"
  default     = ""  # can leave empty if you generate dynamically from ALB
}

variable "task_role_arn" {
  type        = string
  description = "IAM role for ECS task permissions"
}