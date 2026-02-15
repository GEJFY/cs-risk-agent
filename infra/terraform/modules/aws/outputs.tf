output "ecs_cluster_arn" {
  value = aws_ecs_cluster.main.arn
}

output "secrets_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}

output "bedrock_log_group" {
  value = aws_cloudwatch_log_group.bedrock.name
}

output "task_role_arn" {
  value = aws_iam_role.ecs_task.arn
}
