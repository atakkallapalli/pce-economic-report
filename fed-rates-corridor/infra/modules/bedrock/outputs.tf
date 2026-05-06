output "execution_role_arn" {
  description = "ECS execution role ARN"
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "ECS task role ARN (with Bedrock access)"
  value       = aws_iam_role.task.arn
}
