# -*- coding: utf-8 -*-
"""Testes do orquestrador — providers substituídos por fakes determinísticos."""

import asyncio

import pytest

from orchestrator import Orchestrator
from providers.base_provider import BaseProvider, ProviderResult


class _Fake(BaseProvider):
    """Provider fake com latência e resultado controlados."""

    def __init__(self, name, answer="ok", delay=0.0, fail=False):
        super().__init__()
        self.name = name
        self.default_model = f"{name}-model"
        self._answer = answer
        self._delay = delay
        self._fail = fail

    async def _invoke(self, prompt):
        await asyncio.sleep(self._delay)
        if self._fail:
            raise RuntimeError("falha forçada")
        return self._answer, 10, 10, self.default_model


@pytest.fixture
def orch():
    o = Orchestrator()
    o.providers = {
        "aws": _Fake("aws", answer="resp-aws", delay=0.05),
        "oci": _Fake("oci", answer="resp-oci", delay=0.20),
        "gcp": _Fake("gcp", answer="resp-gcp", delay=0.02),
    }
    return o


@pytest.mark.asyncio
async def test_query_parallel_consulta_todos(orch):
    results = await orch.query_parallel(["aws", "oci", "gcp"], "pergunta")
    assert set(results.keys()) == {"aws", "oci", "gcp"}
    assert all(r.ok for r in results.values())
    assert results["aws"].answer == "resp-aws"


@pytest.mark.asyncio
async def test_query_fastest_retorna_o_mais_rapido(orch):
    # gcp tem o menor delay (0.02), deve vencer.
    result = await orch.query_fastest(["aws", "oci", "gcp"], "pergunta")
    assert result.ok
    assert result.cloud == "gcp"


@pytest.mark.asyncio
async def test_query_fastest_ignora_falha_e_pega_proximo():
    o = Orchestrator()
    o.providers = {
        "aws": _Fake("aws", delay=0.01, fail=True),   # falha rápido
        "gcp": _Fake("gcp", answer="vencedor", delay=0.10),
    }
    result = await o.query_fastest(["aws", "gcp"], "x")
    assert result.ok
    assert result.cloud == "gcp"


@pytest.mark.asyncio
async def test_query_consensus_sintetiza(orch):
    consensus, results = await orch.query_consensus(["aws", "oci", "gcp"], "pergunta")
    assert isinstance(consensus, str) and len(consensus) > 0
    assert set(results.keys()) == {"aws", "oci", "gcp"}


@pytest.mark.asyncio
async def test_calculate_total_cost():
    results = {
        "aws": ProviderResult(cloud="aws", cost_usd=0.001),
        "gcp": ProviderResult(cloud="gcp", cost_usd=0.002),
    }
    assert Orchestrator.calculate_total_cost(results) == pytest.approx(0.003)


@pytest.mark.asyncio
async def test_health_reporta_por_cloud(orch):
    h = await orch.health()
    assert h == {"aws": "ok", "oci": "ok", "gcp": "ok"}


def test_models_lista_um_por_cloud(orch):
    m = orch.models()
    assert m["aws"] == ["aws-model"]
