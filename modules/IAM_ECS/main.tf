# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_execution_role" {
  name = "linguaflow-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Attach the managed policy for ECS task execution (CloudWatch logs + ECR)
resource "aws_iam_role_policy_attachment" "ecs_execution_role_attach" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_policy" "ecs_s3_policy" {
  name        = "ecs-s3-access"
  description = "Allow ECS tasks to read/write translation buckets"

  policy = jsonencode({
  Version = "2012-10-17",
  Statement = [
    {
      Effect = "Allow",
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      Resource = [
        var.input_bucket_arn,
        "${var.input_bucket_arn}/*",
        var.responses_bucket_arn,
        "${var.responses_bucket_arn}/*"
      ]
    },
    {
  "Effect": "Allow",
  "Action": ["translate:TranslateText", "s3:PutObject", "s3:GetObject", "s3:ListBucket"],
  "Resource": "*"
}
  ]
})
}

resource "aws_iam_role_policy_attachment" "ecs_s3_attach" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = aws_iam_policy.ecs_s3_policy.arn
}

resource "aws_iam_role" "ecs_task_role" {
  name = "linguaflow-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "ecs-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob",
          "polly:SynthesizeSpeech",
          "translate:TranslateText"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource = [
          "${var.input_bucket_arn}/*",
          "${var.responses_bucket_arn}/*"
        ]
      }
    ]
  })
}