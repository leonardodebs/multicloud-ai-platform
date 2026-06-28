# -*- coding: utf-8 -*-
"""
API FastAPI da plataforma multicloud de IA.

Expõe a interface unificada que consulta AWS Bedrock, OCI GenAI e GCP Vertex AI
simultaneamente, com três modos: comparar, consenso e mais rápido. Mantém
estatísticas de uso em memória para o dashboard do frontend.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from orchestrator import Orchestrator
from providers import ProviderResult

# Instância única do orquestrador (reusa clientes de SDK entre requisições).
orchestrator = Orchestrator()


# ---------------------------------------------------------------------------- #
# Estatísticas em memória (resetam ao reiniciar o processo)
# ---------------------------------------------------------------------------- #
class Stats:
    """Coletor simples de métricas de uso para o endpoint /stats."""

    def __init__(self) -> None:
        self.total_queries = 0
        self.by_cloud: dict[str, int] = defaultdict(int)
        self.by_mode: dict[str, int] = defaultdict(int)
        self.total_latency_ms = 0.0
        self.latency_samples = 0
        self.total_cost_usd = 0.0
        self.queries_by_day: dict[str, int] = defaultdict(int)

    def record(
        self, mode: str, results: dict[str, ProviderResult], cost: float
    ) -> None:
        self.total_queries += 1
        self.by_mode[mode] += 1
        today = dt.date.today().isoformat()
        self.queries_by_day[today] += 1
        self.total_cost_usd += cost
        for cloud, res in results.items():
            self.by_cloud[cloud] += 1
            if res.latency_ms:
                self.total_latency_ms += res.latency_ms
                self.latency_samples += 1

    def snapshot(self) -> dict:
        avg = (
            self.total_latency_ms / self.latency_samples
            if self.latency_samples
            else 0.0
        )
        today = dt.date.today().isoformat()
        return {
            "total_queries": self.total_queries,
            "by_cloud": dict(self.by_cloud),
            "by_mode": dict(self.by_mode),
            "avg_latency_ms": round(avg, 1),
            "total_cost_usd": round(self.total_cost_usd, 8),
            "queries_today": self.queries_by_day.get(today, 0),
        }


stats = Stats()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Hook de ciclo de vida (espaço para inicialização/limpeza futura)."""
    yield


app = FastAPI(
    title="Multicloud AI Platform",
    description="Consulta AWS Bedrock, OCI GenAI e GCP Vertex AI simultaneamente.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS liberado para o frontend (em produção o nginx serve na mesma origem).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------- #
# Modelos de request/response (Pydantic)
# ---------------------------------------------------------------------------- #
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pergunta do usuário")
    clouds: list[str] = Field(
        default_factory=lambda: ["aws", "oci", "gcp"],
        description="Clouds a consultar",
    )
    mode: Literal["compare", "consensus", "fastest"] = "compare"


class RAGRequest(BaseModel):
    question: str = Field(..., min_length=1)
    cloud: Literal["aws", "oci", "gcp"] = "aws"
    documents: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------- #
# Endpoints
# ---------------------------------------------------------------------------- #
@app.post("/query")
async def query(req: QueryRequest) -> dict:
    """
    Consulta multicloud nos três modos.

    - compare:   resultados lado a lado de cada cloud.
    - consensus: resultados + síntese única feita pelo Claude.
    - fastest:   apenas a primeira resposta válida (menor latência).
    """
    if req.mode == "fastest":
        result = await orchestrator.query_fastest(req.clouds, req.question)
        results = {result.cloud: result} if result.cloud != "none" else {}
        cost = orchestrator.calculate_total_cost(results)
        stats.record("fastest", results, cost)
        return {
            "question": req.question,
            "mode": "fastest",
            "results": {c: r.to_dict() for c, r in results.items()},
            "total_cost_usd": cost,
        }

    if req.mode == "consensus":
        consensus, results = await orchestrator.query_consensus(
            req.clouds, req.question
        )
        cost = orchestrator.calculate_total_cost(results)
        stats.record("consensus", results, cost)
        return {
            "question": req.question,
            "mode": "consensus",
            "results": {c: r.to_dict() for c, r in results.items()},
            "consensus": consensus,
            "total_cost_usd": cost,
        }

    # Padrão: comparar.
    results = await orchestrator.query_parallel(req.clouds, req.question)
    cost = orchestrator.calculate_total_cost(results)
    stats.record("compare", results, cost)
    return {
        "question": req.question,
        "mode": "compare",
        "results": {c: r.to_dict() for c, r in results.items()},
        "total_cost_usd": cost,
    }


@app.post("/rag")
async def rag(req: RAGRequest) -> dict:
    """
    RAG simples: injeta os documentos fornecidos como contexto e responde a
    pergunta usando o cloud escolhido. As fontes (índices dos documentos
    usados) são devolvidas para rastreabilidade.
    """
    provider = orchestrator.providers[req.cloud]

    if req.documents:
        contexto = "\n\n".join(
            f"[Documento {i + 1}]\n{doc}" for i, doc in enumerate(req.documents)
        )
        prompt = (
            "Use APENAS o contexto abaixo para responder. Se a resposta não "
            "estiver no contexto, diga que não sabe.\n\n"
            f"## Contexto:\n{contexto}\n\n"
            f"## Pergunta:\n{req.question}\n\n## Resposta:"
        )
        sources = list(range(1, len(req.documents) + 1))
    else:
        prompt = req.question
        sources = []

    result = await provider.query(prompt)
    stats.record("rag", {req.cloud: result}, result.cost_usd)
    return {
        "answer": result.answer,
        "sources": sources,
        "tokens": result.tokens,
        "cost_usd": result.cost_usd,
        "cloud": req.cloud,
        "latency_ms": result.latency_ms,
        "error": result.error,
    }


@app.get("/health")
async def health() -> dict:
    """Saúde geral + status por cloud (usado pelo ALB e pelo HealthIndicator)."""
    clouds = await orchestrator.health()
    overall = "ok" if all(v == "ok" for v in clouds.values()) else "degraded"
    return {"status": overall, "clouds": clouds}


@app.get("/stats")
async def get_stats() -> dict:
    """Estatísticas agregadas de uso para o StatsDashboard."""
    return stats.snapshot()


@app.get("/models")
async def models() -> dict:
    """Lista os modelos disponíveis por cloud."""
    return orchestrator.models()
