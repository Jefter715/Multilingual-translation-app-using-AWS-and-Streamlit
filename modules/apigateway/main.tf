# REST API
resource "aws_api_gateway_rest_api" "api" {
  name = "translation-api"
}

# Resource (proxy)
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "translate"
}

# Method
resource "aws_api_gateway_method" "method" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "POST"
  authorization = "NONE"
}

# HTTP Proxy Integration (ECS)
resource "aws_api_gateway_integration" "http_proxy" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.proxy.id
  http_method = aws_api_gateway_method.method.http_method

  type                    = "HTTP_PROXY"
  integration_http_method = "POST"
  uri = "http://translation-api-alb-459176700.us-east-1.elb.amazonaws.com/translate"

  passthrough_behavior = "WHEN_NO_MATCH"
}

# Deployment
resource "aws_api_gateway_deployment" "deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  triggers = {
    redeploy = timestamp()
  }

  depends_on = [
    aws_api_gateway_integration.http_proxy,
    aws_api_gateway_method.method
  ]
  lifecycle {
    create_before_destroy = true
  }
}

# Stage
resource "aws_api_gateway_stage" "stage" {
  stage_name    = "prod"
  rest_api_id   = aws_api_gateway_rest_api.api.id
  deployment_id = aws_api_gateway_deployment.deployment.id
}