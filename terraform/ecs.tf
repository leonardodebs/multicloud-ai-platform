# ECS Fargate — cluster, task definition (2 containers) e service.

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Task com DOIS containers na mesma task (rede awsvpc → comunicação via
# localhost): backend FastAPI (8000) + frontend nginx (80). O nginx faz proxy
# de /api e /health para 127.0.0.1:8000.
resource "aws_ecs_task_definition" "main" {
  family                   = var.project_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name         = "backend"
      image        = local.backend_image
      essential    = true
      memory       = 384
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      environment = [
        { name = "DEMO_MODE", value = tostring(var.demo_mode) },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
        { name = "MAX_TOKENS", value = "1024" }
      ]
      # Credenciais OCI/GCP injetadas a partir do Secrets Manager (vazias em
      # modo demo). A AWS usa a task role, sem secret.
      secrets = [
        { name = "OCI_CREDENTIALS_JSON", valueFrom = aws_secretsmanager_secret.oci.arn },
        { name = "GCP_CREDENTIALS_JSON", valueFrom = aws_secretsmanager_secret.gcp.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 15
      }
    },
    {
      name         = "frontend"
      image        = local.frontend_image
      essential    = true
      memory       = 128
      portMappings = [{ containerPort = 80, protocol = "tcp" }]
      environment = [
        { name = "BACKEND_HOST", value = "127.0.0.1" },
        { name = "BACKEND_PORT", value = "8000" }
      ]
      # Só sobe o frontend depois que o backend estiver saudável.
      dependsOn = [{ containerName = "backend", condition = "HEALTHY" }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true # necessário para puxar imagens do ECR sem NAT
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main.arn
    container_name   = "frontend"
    container_port   = 80
  }

  # Espera o registro no target group antes de marcar como estável.
  health_check_grace_period_seconds = 60

  depends_on = [aws_lb_listener.http]
}
