# Versões de provider e configuração do Terraform.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend remoto recomendado em produção (descomente e ajuste):
  # backend "s3" {
  #   bucket = "meu-bucket-tfstate"
  #   key    = "multicloud-ai/terraform.tfstate"
  #   region = "us-west-2"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "Terraform"
    }
  }
}
