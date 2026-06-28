# Saídas — principalmente a URL pública do demo (alb_dns_name).

output "alb_dns_name" {
  description = "URL pública do demo (DNS do ALB)."
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecr_backend_url" {
  description = "URL do repositório ECR do backend."
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "URL do repositório ECR do frontend."
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "Nome do cluster ECS."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Nome do serviço ECS."
  value       = aws_ecs_service.main.name
}

output "github_deploy_role_arn" {
  description = "ARN da role assumida pelo GitHub Actions (OIDC) no deploy."
  value       = aws_iam_role.github_deploy.arn
}
