output "input_bucket_arn" {
  value = module.s3.input_bucket_arn
}

output "responses_bucket_arn" {
  value = module.s3.responses_bucket_arn
}

output "ecs_url" {
  value = module.ecs.load_balancer_url
}

output "api_url" {
  value = module.apigateway.api_url
}
/*
output "sqs_queue_url" {
  value = module.sqs.sqs_queue_url
}
*/
output "transcribe_enabled" {
  value = true
}

output "polly_enabled" {
  value = true
}

