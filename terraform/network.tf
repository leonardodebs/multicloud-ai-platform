# Rede — usa a VPC default e suas subnets públicas para evitar custos de
# NAT Gateway (mantém o alvo de ~$10/mês). As tasks Fargate recebem IP público
# para baixar as imagens do ECR.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security group do ALB: aceita HTTP da internet.
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Permite HTTP de entrada para o ALB"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security group das tasks ECS: aceita tráfego na porta 80 (frontend/nginx)
# apenas vindo do ALB. O backend é acessado via localhost dentro da task.
resource "aws_security_group" "ecs" {
  name        = "${var.project_name}-ecs-sg"
  description = "Permite trafego do ALB para as tasks ECS"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "HTTP do ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
