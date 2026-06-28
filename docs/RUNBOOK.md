# 📕 Runbook Operacional

Procedimentos operacionais e troubleshooting da **Multicloud AI Platform**.

> Convenção: comandos assumem o diretório raiz do projeto
> (`multicloud-bridge/`) salvo indicação contrária.

---

## Índice

1. [Operação local (docker-compose)](#1-operação-local-docker-compose)
2. [Desenvolvimento (hot reload)](#2-desenvolvimento-hot-reload)
3. [Testes](#3-testes)
4. [Deploy em produção (AWS)](#4-deploy-em-produção-aws)
5. [Rollback](#5-rollback)
6. [Observabilidade (logs e métricas)](#6-observabilidade-logs-e-métricas)
7. [Troubleshooting](#7-troubleshooting)
8. [Verificações de saúde (health checks)](#8-verificações-de-saúde)

---

## 1. Operação local (docker-compose)

### Subir

```bash
docker compose up --build          # primeira vez (ou após mudar código)
docker compose up -d               # background, sem rebuild
```

⚠️ **Conflito de porta neste host:** as portas **80** e **8080** já estão
ocupadas por clusters Kubernetes de laboratório (`girus`, `giropops`,
`lab-control-plane`). Sempre suba o frontend em outra porta:

```bash
FRONTEND_PORT=8090 docker compose up -d
# Acesse: http://localhost:8090
```

### Verificar status

```bash
docker compose ps
# backend  → "Up (healthy)"   na 8000
# frontend → "Up"             na porta escolhida → 80
```

### Parar / remover

```bash
docker compose down                # para e remove containers + rede
docker compose down -v             # idem + volumes (se houver)
```

### Smoke test rápido

```bash
PORT=8090
curl -s http://localhost:$PORT/health
curl -s -X POST http://localhost:$PORT/api/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"ping","clouds":["aws","oci","gcp"],"mode":"compare"}'
```

---

## 2. Desenvolvimento (hot reload)

```bash
docker compose -f docker-compose.dev.yml up
```

- Backend (uvicorn `--reload`): http://localhost:8000 — Swagger em `/docs`.
- Frontend (Vite HMR): http://localhost:5173.

Edição de `.py` ou `.jsx` recarrega automaticamente. O proxy do Vite encaminha
`/api` → `backend:8000` dentro da rede do compose.

---

## 3. Testes

### Backend (23 testes, modo demo, sem rede)

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
DEMO_MODE=true pytest -q
```

### Frontend (lint + testes + build)

```bash
cd frontend
npm install
npm run lint
npm test
npm run build
```

### Tudo de uma vez (como o CI faz)

Equivalente ao `ci.yml`: backend pytest → frontend eslint/vitest/build →
trivy → checkov → `terraform validate`.

```bash
cd terraform && terraform fmt -check -recursive && \
  terraform init -backend=false && terraform validate
```

---

## 4. Deploy em produção (AWS)

### Pré-requisitos (uma vez)

1. Conta AWS com permissão de admin para o `apply` inicial.
2. `terraform apply` inicial **local** para criar ECR, IAM e a role OIDC:
   ```bash
   cd terraform
   terraform init
   terraform apply
   # anote os outputs: ecr_*_url, github_deploy_role_arn, alb_dns_name
   ```
3. No GitHub, criar o secret **`AWS_DEPLOY_ROLE_ARN`** com o valor de
   `terraform output -raw github_deploy_role_arn`.
4. Conferir/ajustar a variável `github_repo` em `variables.tf` (owner/repo).

### Deploy contínuo (automático)

Push em `main` dispara `deploy.yml`, que:

1. Assume a role via **OIDC** (sem credenciais armazenadas).
2. Faz build e push das imagens no ECR (tag = SHA curto do commit).
3. Roda `terraform apply` passando `backend_image` e `frontend_image`.
4. `aws ecs wait services-stable`.
5. **Smoke test:** `GET /health` deve retornar `status: ok`.
6. Atualiza o README com a URL do demo (entre os marcadores `LIVE_DEMO`).

### Deploy manual (workflow_dispatch)

GitHub → Actions → **Deploy** → *Run workflow*.

### Deploy local de emergência (sem o pipeline)

```bash
REGION=us-west-2
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REG=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com
TAG=$(git rev-parse --short HEAD)

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REG

docker build -f Dockerfile.backend  -t $REG/multicloud-ai-backend:$TAG .
docker build -f Dockerfile.frontend -t $REG/multicloud-ai-frontend:$TAG .
docker push $REG/multicloud-ai-backend:$TAG
docker push $REG/multicloud-ai-frontend:$TAG

cd terraform
terraform apply \
  -var="backend_image=$REG/multicloud-ai-backend:$TAG" \
  -var="frontend_image=$REG/multicloud-ai-frontend:$TAG"
```

---

## 5. Rollback

### Opção A — reapontar para a imagem anterior

```bash
cd terraform
terraform apply \
  -var="backend_image=<REG>/multicloud-ai-backend:<SHA_ANTERIOR>" \
  -var="frontend_image=<REG>/multicloud-ai-frontend:<SHA_ANTERIOR>"
```

### Opção B — voltar a task definition anterior (rápido, via AWS CLI)

```bash
CLUSTER=multicloud-ai-cluster
SERVICE=multicloud-ai-service
# Liste as revisões e escolha a anterior
aws ecs list-task-definitions --family-prefix multicloud-ai --sort DESC
aws ecs update-service --cluster $CLUSTER --service $SERVICE \
  --task-definition multicloud-ai:<REVISAO_ANTERIOR>
aws ecs wait services-stable --cluster $CLUSTER --services $SERVICE
```

> Depois de um rollback via CLI, rode `terraform plan` para reconciliar o estado.

---

## 6. Observabilidade (logs e métricas)

### Local

```bash
docker compose logs -f             # tudo
docker compose logs -f backend     # só o backend
docker compose logs --tail=50 frontend
```

### AWS (CloudWatch)

- Log groups: `/ecs/multicloud-ai/backend` e `/ecs/multicloud-ai/frontend`
  (retenção de 14 dias).
- Dashboard: **`multicloud-ai-dashboard`** — CPU/memória do ECS e
  requisições/latência do ALB.

```bash
# Tail dos logs do backend
aws logs tail /ecs/multicloud-ai/backend --follow

# Estado do serviço ECS
aws ecs describe-services --cluster multicloud-ai-cluster \
  --services multicloud-ai-service \
  --query 'services[0].{running:runningCount,desired:desiredCount,deployments:deployments[].status}'
```

### Métricas internas da aplicação

```bash
curl -s http://<host>/stats        # total de consultas, latência média, custo
```

---

## 7. Troubleshooting

### 7.1 Frontend fica em "Created" e não sobe / "port is already allocated"

**Sintoma:** `docker compose ps` mostra `backend Up (healthy)` mas
`frontend Created`, e o `up` exibiu
`Bind for 0.0.0.0:80 failed: port is already in use`.

**Causa:** a porta do host já está ocupada (neste ambiente, 80 e 8080 estão
tomadas por clusters k8s de laboratório).

**Diagnóstico:**
```bash
ss -ltn | grep -E ':(80|8080) '          # ver portas ocupadas
docker ps --format "table {{.Names}}\t{{.Ports}}"   # quem segura cada porta
```

**Correção:** usar uma porta livre (≥ 8090):
```bash
docker compose down
FRONTEND_PORT=8090 docker compose up -d
```

### 7.2 Backend `unhealthy`

**Diagnóstico:**
```bash
docker compose logs backend | tail -30
docker compose exec backend curl -s http://localhost:8000/health
```

**Causas comuns:** erro de import, porta 8000 ocupada no host, dependência
faltando. Em modo demo, `/health` sempre retorna os 3 clouds `ok`.

### 7.3 Respostas vêm com "[DEMO]" mesmo querendo modelos reais

**Causa:** a plataforma está em modo demo. Acontece quando:
- `DEMO_MODE=true` (padrão), ou
- faltam credenciais resolvíveis para a nuvem, ou
- faltam variáveis obrigatórias (`OCI_COMPARTMENT_ID`, `GCP_PROJECT_ID`).

**Correção:** copie `.env.example` → `.env`, preencha as credenciais e defina
`DEMO_MODE=false`. Veja `docs/VARIAVEIS_DE_AMBIENTE.md`. Reinicie:
```bash
docker compose up -d --force-recreate
```

### 7.4 Um cloud específico responde com `error`

Lembre: **isso é esperado e não derruba a requisição** — os outros clouds
respondem normalmente. Verifique o campo `error` no resultado.

| `error` contém | Provável causa |
| -------------- | -------------- |
| `timeout` | modelo lento / rede; a base já tentou 2x |
| `Throttl`/`rate` | throttling do provedor; reduza a frequência |
| `AccessDenied`/`Unauthorized` | credencial/role sem permissão no serviço de IA |
| `ResourceNotFound`/`model` | ID de modelo inválido na região |

### 7.5 Deploy: serviço ECS não estabiliza

```bash
aws ecs describe-services --cluster multicloud-ai-cluster \
  --services multicloud-ai-service --query 'services[0].events[:5]'
# e os logs:
aws logs tail /ecs/multicloud-ai/backend --since 10m
```

**Causas comuns:**
- Imagem não encontrada no ECR (tag errada).
- Task sem IP público em subnet sem rota para internet → falha ao puxar ECR
  (confirme `assign_public_ip = true` e subnets públicas).
- Backend não fica HEALTHY → frontend (que tem `dependsOn`) nunca sobe.
- Memória insuficiente (task tem 512MB; backend reserva 384). Se OOM, aumente
  `task_memory`.

### 7.6 Smoke test do deploy falha (`/health` não retorna ok)

```bash
ALB=$(cd terraform && terraform output -raw alb_dns_name)
curl -v $ALB/health
```

- Target group `unhealthy`? O health check é `GET /health` → nginx → backend.
  Confira se o backend está respondendo e se o SG do ECS aceita o ALB.
- Em modo demo (`demo_mode = true`, padrão no Terraform), `/health` deve
  sempre retornar `ok` — se não retornar, o problema é de rede/infra, não da app.

### 7.7 ECR "denied" no push (pipeline)

- Confira o secret `AWS_DEPLOY_ROLE_ARN` no GitHub.
- Confira `github_repo` em `variables.tf` (a condição OIDC `sub` precisa bater
  com `repo:owner/repo:*`).

### 7.8 Terraform "port/bind"/state lock

```bash
terraform force-unlock <LOCK_ID>   # se o state ficou travado
terraform plan                     # reconciliar drift
```

---

## 8. Verificações de saúde

| O quê | Como |
| ----- | ---- |
| App local | `curl http://localhost:<porta>/health` |
| App produção | `curl $(cd terraform && terraform output -raw alb_dns_name)/health` |
| Container backend | `docker compose ps` → coluna STATUS `(healthy)` |
| Serviço ECS | `aws ecs describe-services ... running == desired` |
| Target group | console EC2 → Target Groups → `multicloud-ai-tg` → healthy |

**Resposta esperada de `/health`:**
```json
{"status":"ok","clouds":{"aws":"ok","oci":"ok","gcp":"ok"}}
```

`status` pode ser `degraded` se algum cloud reportar `error` (com credenciais
reais). Em modo demo, sempre `ok`.

---

## Referência rápida de comandos

```bash
# Local
FRONTEND_PORT=8090 docker compose up -d   # subir (porta livre)
docker compose logs -f backend            # logs
docker compose down                       # parar

# Testes
cd backend && DEMO_MODE=true pytest -q
cd frontend && npm run lint && npm test && npm run build

# AWS
aws logs tail /ecs/multicloud-ai/backend --follow
aws ecs wait services-stable --cluster multicloud-ai-cluster --services multicloud-ai-service
cd terraform && terraform output -raw alb_dns_name
```
