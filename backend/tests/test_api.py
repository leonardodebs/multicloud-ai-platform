# -*- coding: utf-8 -*-
"""Testes dos endpoints FastAPI (em modo demo, sem rede)."""

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert set(body["clouds"].keys()) == {"aws", "oci", "gcp"}


def test_models():
    r = client.get("/models")
    assert r.status_code == 200
    body = r.json()
    assert "aws" in body and "oci" in body and "gcp" in body


def test_query_compare():
    r = client.post(
        "/query",
        json={"question": "Capital do Brasil?", "clouds": ["aws", "gcp"], "mode": "compare"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "compare"
    assert set(body["results"].keys()) == {"aws", "gcp"}
    assert "total_cost_usd" in body


def test_query_consensus_inclui_sintese():
    r = client.post(
        "/query",
        json={"question": "O que é multicloud?", "clouds": ["aws", "oci", "gcp"], "mode": "consensus"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "consensus"
    assert "consensus" in body
    assert isinstance(body["consensus"], str)


def test_query_fastest_retorna_um():
    r = client.post(
        "/query",
        json={"question": "ping", "clouds": ["aws", "oci", "gcp"], "mode": "fastest"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "fastest"
    assert len(body["results"]) == 1


def test_rag_com_documentos():
    r = client.post(
        "/rag",
        json={
            "question": "Qual o prazo?",
            "cloud": "aws",
            "documents": ["O prazo de entrega é 5 dias.", "Frete grátis acima de R$200."],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cloud"] == "aws"
    assert body["sources"] == [1, 2]
    assert body["answer"] is not None


def test_stats_apos_consultas():
    # As chamadas anteriores já alimentaram o coletor de estatísticas.
    r = client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total_queries"] >= 1
    assert "by_cloud" in body and "by_mode" in body
    assert "avg_latency_ms" in body


def test_query_rejeita_pergunta_vazia():
    r = client.post("/query", json={"question": "", "clouds": ["aws"], "mode": "compare"})
    assert r.status_code == 422  # validação Pydantic (min_length=1)
