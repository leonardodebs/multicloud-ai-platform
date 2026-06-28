# Variáveis de entrada da infraestrutura.

variable "aws_region" {
  description = "Região AWS para todos os recursos."
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Prefixo de nomes dos recursos."
  type        = string
  default     = "multicloud-ai"
}

variable "backend_image" {
  description = "Imagem do backend no ECR (tag completa). Definida no deploy."
  type        = string
  default     = ""
}

variable "frontend_image" {
  description = "Imagem do frontend no ECR (tag completa). Definida no deploy."
  type        = string
  default     = ""
}

variable "task_cpu" {
  description = "vCPU da task Fargate (256 = 0.25 vCPU)."
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Memória da task Fargate em MB."
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Número de tasks ECS desejadas."
  type        = number
  default     = 1
}

variable "demo_mode" {
  description = "Roda a plataforma em modo demo (sem credenciais de cloud reais)."
  type        = bool
  default     = true
}

variable "github_repo" {
  description = "Repositório GitHub (owner/repo) autorizado a assumir a role OIDC de deploy."
  type        = string
  default     = "leonardodebs/multicloud-ai-platform"
}

variable "log_retention_days" {
  description = "Retenção dos logs no CloudWatch."
  type        = number
  default     = 14
}
