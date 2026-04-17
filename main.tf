provider "aws" {
  region = var.aws_region
}

# --- S3 ---
module "s3" {
  source = "./modules/s3"

  input_bucket_name     = var.input_bucket_name
  responses_bucket_name = var.responses_bucket_name
}

/*# --- SQS ---
module "sqs" {
  source     = "./modules/sqs"
  queue_name = "translation-batch-queue"
}*/

# --- IAM (General App Role) ---
module "iam" {
  source = "./modules/iam"

  role_name  = var.app_role_name
  s3_buckets = [module.s3.input_bucket_arn, module.s3.responses_bucket_arn]
}

# --- ECS Execution Role ---
module "ecs_execution_role" {
  source               = "./modules/iam_ecs"
  input_bucket_arn     = module.s3.input_bucket_arn
  responses_bucket_arn = module.s3.responses_bucket_arn

}

# --- ECS ---
module "ecs" {
  source = "./modules/ecs"

  image_url             = var.ecs_image_url
  execution_role_arn    = module.ecs_execution_role.execution_role_arn
  subnets               = var.subnets
  vpc_id                = var.vpc_id
  input_bucket_name     = var.input_bucket_name
  responses_bucket_name = var.responses_bucket_name
  aws_region            = var.aws_region
  task_role_arn         = module.ecs_execution_role.task_role_arn

}

# --- API Gateway ---
module "apigateway" {
  source = "./modules/apigateway"

  region                = var.aws_region
  ecs_load_balancer_url = module.ecs.load_balancer_url

  depends_on = [module.ecs]
}

