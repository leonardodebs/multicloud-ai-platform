# Secrets Manager — credenciais de OCI e GCP.
# AWS NÃO precisa de secret: a task usa a IAM role (task role) para o Bedrock.
#
# Os valores ficam vazios por padrão (modo demo). Para usar modelos reais,
# preencha os secrets no console/CLI e ajuste demo_mode = false.

resource "aws_secretsmanager_secret" "oci" {
  name        = "${var.project_name}/oci-credentials"
  description = "Config e chave da API OCI (Generative AI)"
}

resource "aws_secretsmanager_secret_version" "oci" {
  secret_id     = aws_secretsmanager_secret.oci.id
  secret_string = jsonencode({ placeholder = "preencha-com-config-oci" })
}

resource "aws_secretsmanager_secret" "gcp" {
  name        = "${var.project_name}/gcp-credentials"
  description = "Service account JSON do GCP (Vertex AI)"
}

resource "aws_secretsmanager_secret_version" "gcp" {
  secret_id     = aws_secretsmanager_secret.gcp.id
  secret_string = jsonencode({ placeholder = "preencha-com-service-account-json" })
}
