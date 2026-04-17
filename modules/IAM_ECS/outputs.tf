output "execution_role_arn" {
  value       = aws_iam_role.ecs_execution_role.arn
  description = "ARN of the ECS execution role"
}
output "task_role_arn" {
  value = aws_iam_role.ecs_task_role.arn
}