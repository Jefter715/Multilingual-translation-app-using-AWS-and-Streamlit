output "api_url" {
  description = "Invoke URL of the API Gateway"
  value       = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.region}.amazonaws.com/${aws_api_gateway_stage.stage.stage_name}"
}