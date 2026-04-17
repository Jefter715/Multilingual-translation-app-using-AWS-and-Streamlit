output "input_bucket_arn" {
  value = aws_s3_bucket.input.arn
}

output "responses_bucket_arn" {
  value = aws_s3_bucket.responses.arn
}