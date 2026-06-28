# ⚙️ Variáveis de Ambiente

Template e referência de configuração da **Multicloud AI Platform**.

> 🔐 **Nunca** faça commit do arquivo `.env` (já está no `.gitignore`). Use o
> `.env.example` como base e mantenha segredos fora do versionamento.

---

## 1. Início rápido

```bash
cp .env.example .env
# edite .env conforme as tabelas abaixo
FRONTEND_PORT=8090 docker compose up -d
```

Sem nenhuma credencial, a plataforma roda em **modo demo** (respostas
sintéticas) — perfeito para testar a interface sem contas de nuvem.

---

## 2. Aplicação (backend)

| Variável | Obrigatória | Padrão | Descrição |
| -------- | ----------- | ------ | --------- |
| `DEMO_MODE` | não | `true` | `true` = respostas sintéticas (sem chamar nuvens). Defina `false` para usar modelos reais. |
| `MAX_TOKENS` | não | `1024` | Limite de tokens de saída por chamada (todos os clouds). |

> Quando `DEMO_MODE=false`, cada cloud ainda cai em demo **individualmente** se
> faltar sua credencial/configuração — só consultam de verdade os que estiverem
> configurados.

---

## 3. AWS Bedrock — Claude Haiku 4.5

A AWS usa a **cadeia de credenciais padrão do boto3**. Em produção/ECS, o ideal
é a **IAM role da task** (sem chaves estáticas).

| Variável | Obrigatória | Padrão | Descrição |
| -------- | ----------- | ------ | --------- |
| `AWS_DEFAULT_REGION` | sim (real) | `us-west-2` | Região do Bedrock. |
| `AWS_ACCESS_KEY_ID` | local apenas | — | Chave de acesso (em dev local). No ECS use a task role. |
| `AWS_SECRET_ACCESS_KEY` | local apenas | — | Chave secreta (em dev local). |
| `AWS_BEDROCK_MODEL_ID` | não | `us.anthropic.claude-haiku-4-5` | Sobrescreve o inference profile padrão. |

> ⚠️ É preciso ter **acesso ao modelo habilitado** no Bedrock para a região
> escolhida (console Bedrock → Model access).

---

## 4. OCI Generative AI — Cohere Command R

A OCI lê o arquivo de config (`~/.oci/config`). Para uso real, esse arquivo
precisa estar acessível ao container (volume) e o compartment definido.

| Variável | Obrigatória | Padrão | Descrição |
| -------- | ----------- | ------ | --------- |
| `OCI_COMPARTMENT_ID` | sim (real) | — | OCID do compartment. **Sem ele, o provider entra em demo.** |
| `OCI_REGION` | não | `us-chicago-1` | Região do serviço de inferência. |
| `OCI_MODEL_ID` | não | `cohere.command-r-08-2024` | Modelo a usar. |
| `OCI_CONFIG_FILE` | não | `~/.oci/config` | Caminho do arquivo de config OCI. |
| `OCI_PROFILE` | não | `DEFAULT` | Profile dentro do config. |

---

## 5. GCP Vertex AI — Gemini 1.5 Flash

O GCP usa **Application Default Credentials (ADC)**: aponte
`GOOGLE_APPLICATION_CREDENTIALS` para o JSON da service account.

| Variável | Obrigatória | Padrão | Descrição |
| -------- | ----------- | ------ | --------- |
| `GCP_PROJECT_ID` | sim (real) | — | ID do projeto GCP. **Sem ele, o provider entra em demo.** |
| `GCP_LOCATION` | não | `us-central1` | Região do Vertex AI. |
| `GCP_MODEL_ID` | não | `gemini-1.5-flash` | Modelo a usar. |
| `GOOGLE_APPLICATION_CREDENTIALS` | sim (real) | — | Caminho para o JSON da service account (montado no container). |

---

## 6. Docker Compose / nginx

| Variável | Onde | Padrão | Descrição |
| -------- | ---- | ------ | --------- |
| `FRONTEND_PORT` | host (compose) | `80` | Porta pública do frontend. **Neste host use `8090`** (80 e 8080 estão ocupadas por labs k8s). |
| `BACKEND_HOST` | container frontend | `backend` | Host do backend para o proxy nginx. `backend` (compose) / `127.0.0.1` (ECS). |
| `BACKEND_PORT` | container frontend | `8000` | Porta do backend para o proxy nginx. |
| `VITE_PROXY_TARGET` | dev (frontend) | `http://localhost:8000` | Alvo do proxy do Vite no modo dev. No `docker-compose.dev.yml` é `http://backend:8000`. |

---

## 7. Template `.env` (copie e preencha)

```dotenv
# ===========================================================================
# Multicloud AI Platform — configuração
# Copie para .env. SEM credenciais, roda em MODO DEMO.
# ===========================================================================

# --- Aplicação ------------------------------------------------------------
DEMO_MODE=true          # false = usa modelos reais
MAX_TOKENS=1024
# FRONTEND_PORT=8090    # porta pública do frontend (evite 80/8080 neste host)

# --- AWS Bedrock (Claude Haiku 4.5) ---------------------------------------
AWS_DEFAULT_REGION=us-west-2
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5

# --- OCI Generative AI (Cohere Command R) ---------------------------------
OCI_COMPARTMENT_ID=
OCI_REGION=us-chicago-1
OCI_MODEL_ID=cohere.command-r-08-2024

# --- GCP Vertex AI (Gemini 1.5 Flash) -------------------------------------
GCP_PROJECT_ID=
GCP_LOCATION=us-central1
GCP_MODEL_ID=gemini-1.5-flash
# GOOGLE_APPLICATION_CREDENTIALS=/path/para/service-account.json
```

---

## 8. Produção (ECS) — como as variáveis chegam ao container

No ECS, **não há arquivo `.env`**. A injeção é feita pela task definition
(Terraform):

| Origem | Variáveis |
| ------ | --------- |
| `environment` (texto claro) | `DEMO_MODE`, `AWS_DEFAULT_REGION`, `MAX_TOKENS`, `BACKEND_HOST`, `BACKEND_PORT` |
| `secrets` (Secrets Manager) | `OCI_CREDENTIALS_JSON` ← secret `multicloud-ai/oci-credentials`<br/>`GCP_CREDENTIALS_JSON` ← secret `multicloud-ai/gcp-credentials` |
| **IAM task role** | credenciais AWS (Bedrock) — **sem variável**, é a identidade da task |

Por padrão a task sobe com `demo_mode = true` (variável Terraform), então o demo
ao vivo funciona sem segredos. Para modelos reais:

1. Popular os secrets no Secrets Manager:
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id multicloud-ai/gcp-credentials \
     --secret-string "$(cat service-account.json)"
   ```
2. Definir `demo_mode = false` (variável Terraform) e dar `terraform apply`.
3. Garantir que a **task role** tem permissão de `bedrock:InvokeModel`
   (já incluída no `iam.tf`).

---

## 9. Variáveis do Terraform (`terraform/variables.tf`)

| Variável | Padrão | Descrição |
| -------- | ------ | --------- |
| `aws_region` | `us-west-2` | Região de todos os recursos. |
| `project_name` | `multicloud-ai` | Prefixo dos nomes dos recursos. |
| `backend_image` | `""` | Tag da imagem do backend no ECR (definida no deploy). |
| `frontend_image` | `""` | Tag da imagem do frontend no ECR. |
| `task_cpu` | `256` | vCPU da task (256 = 0.25). |
| `task_memory` | `512` | Memória da task (MB). |
| `desired_count` | `1` | Número de tasks ECS. |
| `demo_mode` | `true` | Roda a app em modo demo no ECS. |
| `github_repo` | `leonardodebs/multicloud-ai-platform` | Repo autorizado na role OIDC (`owner/repo`). |
| `log_retention_days` | `14` | Retenção dos logs no CloudWatch. |

Passe valores via `-var` ou um arquivo `terraform.tfvars`:

```hcl
# terraform/terraform.tfvars (exemplo)
aws_region   = "us-west-2"
demo_mode    = false
github_repo  = "seu-usuario/multicloud-ai-platform"
```

---

## 10. Segredos do GitHub Actions

| Secret | Usado em | Descrição |
| ------ | -------- | --------- |
| `AWS_DEPLOY_ROLE_ARN` | `deploy.yml` | ARN da role assumida via OIDC. Valor = `terraform output -raw github_deploy_role_arn`. **Não é uma chave AWS** — é só o ARN da role. |

> O deploy **não usa** `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` no GitHub: a
> autenticação é via **OIDC** (web identity), sem credenciais estáticas.

---

## 11. Resumo: o que é obrigatório por cenário

| Cenário | Variáveis necessárias |
| ------- | --------------------- |
| **Demo local** (padrão) | nenhuma (talvez `FRONTEND_PORT=8090`) |
| **AWS real (local)** | `DEMO_MODE=false`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` |
| **OCI real (local)** | `DEMO_MODE=false`, `OCI_COMPARTMENT_ID`, `~/.oci/config` montado |
| **GCP real (local)** | `DEMO_MODE=false`, `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` |
| **Deploy AWS (CI/CD)** | secret `AWS_DEPLOY_ROLE_ARN` + `terraform apply` inicial |
