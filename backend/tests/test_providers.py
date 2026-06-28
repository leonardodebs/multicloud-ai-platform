# -*- coding: utf-8 -*-
"""Testes dos providers — todos com _invoke mockado (sem rede/SDK real)."""

import asyncio

import pytest

from providers import AWSProvider, GCPProvider, OCIProvider, ProviderResult
from providers.base_provider import BaseProvider


# Subclasse de teste que controla totalmente o comportamento de _invoke.
class FakeProvider(BaseProvider):
    name = "fake"
    default_model = "fake-model-1"
    price_in_per_mtok = 1.0
    price_out_per_mtok = 2.0

    def __init__(self, behavior="ok", **kwargs):
        super().__init__(**kwargs)
        self.behavior = behavior
        self.calls = 0

    async def _invoke(self, prompt):
        self.calls += 1
        if self.behavior == "ok":
            return "resposta ok", 100, 50, "fake-model-1"
        if self.behavior == "slow":
            await asyncio.sleep(5)  # estoura timeouts curtos
            return "tarde demais", 1, 1, "fake-model-1"
        if self.behavior == "transient_then_ok":
            if self.calls < 2:
                raise RuntimeError("throttling temporário")  # transitório
            return "recuperado", 10, 10, "fake-model-1"
        if self.behavior == "fatal":
            raise ValueError("erro de validação permanente")
        raise RuntimeError("comportamento desconhecido")


@pytest.mark.asyncio
async def test_query_sucesso_calcula_custo_e_latencia():
    p = FakeProvider(behavior="ok")
    res = await p.query("oi")
    assert res.ok
    assert res.answer == "resposta ok"
    assert res.tokens == 150
    # custo = (100*1 + 50*2) / 1e6 = 200/1e6
    assert res.cost_usd == pytest.approx(200 / 1_000_000)
    assert res.latency_ms >= 0


@pytest.mark.asyncio
async def test_query_nunca_levanta_em_erro_fatal():
    p = FakeProvider(behavior="fatal")
    res = await p.query("oi")
    assert not res.ok
    assert res.error is not None
    assert "ValueError" in res.error
    assert p.calls == 1  # erro fatal não deve retentar


@pytest.mark.asyncio
async def test_query_retenta_em_erro_transitorio():
    p = FakeProvider(behavior="transient_then_ok", max_retries=2)
    res = await p.query("oi")
    assert res.ok
    assert res.answer == "recuperado"
    assert p.calls == 2  # falhou uma vez, sucesso na segunda


@pytest.mark.asyncio
async def test_query_respeita_timeout():
    p = FakeProvider(behavior="slow", max_retries=0)
    res = await p.query("oi", timeout=0.1)
    assert not res.ok
    assert "timeout" in (res.error or "")


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", [AWSProvider, OCIProvider, GCPProvider])
async def test_providers_reais_em_modo_demo(cls):
    # DEMO_MODE=true vem do conftest → nenhum SDK/credencial é exigido.
    p = cls()
    res = await p.query("Qual a capital da França?")
    assert res.ok
    assert res.cloud == p.name
    assert "[DEMO]" in res.answer
    assert res.tokens > 0


def test_provider_result_serializa():
    r = ProviderResult(cloud="aws", answer="x", model="m", tokens=3)
    d = r.to_dict()
    assert d["cloud"] == "aws"
    assert d["tokens"] == 3
