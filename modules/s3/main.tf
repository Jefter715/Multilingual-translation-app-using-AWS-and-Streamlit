resource "aws_s3_bucket" "input" {
  bucket = var.input_bucket_name
}

resource "aws_s3_bucket" "responses" {
  bucket = var.responses_bucket_name
}



resource "aws_s3_bucket_policy" "transcribe_access" {
  bucket = aws_s3_bucket.input.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowTranscribeReadInput",
        Effect = "Allow",
        Principal = {
          Service = "transcribe.amazonaws.com"
        },
        Action = "s3:GetObject",
        Resource = "${aws_s3_bucket.input.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "transcribe_output_access" {
  bucket = aws_s3_bucket.responses.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowTranscribeWriteOutput",
        Effect = "Allow",
        Principal = {
          Service = "transcribe.amazonaws.com"
        },
        Action = [
          "s3:PutObject"
        ],
        Resource = "${aws_s3_bucket.responses.arn}/*"
      },
      {
        Sid    = "AllowBucketLocationCheck",
        Effect = "Allow",
        Principal = {
          Service = "transcribe.amazonaws.com"
        },
        Action = "s3:GetBucketLocation",
        Resource = aws_s3_bucket.responses.arn
      }
    ]
  })
}