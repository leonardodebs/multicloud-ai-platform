# -*- coding: utf-8 -*-
"""
Padrão de provider abstrato para os 3 clouds (AWS, OCI, GCP).

Aprendido com oci_vs_others_comparison.py: cada cloud expõe a mesma interface
async para que o orquestrador trate todos de forma uniforme. Nenhum provider
LEVANTA exceção — sempre retorna um ProviderResult, com o erro preenchido em
caso de falha. Isso mantém o asyncio.gather() do orquestrador resiliente.
"""

from __future__ import annotations

import abc
import asyncio
import time
from dataclasses import dataclass, field, asdict
from typing import Any


# Erros considerados transitórios — vale a pena tentar novamente (timeout,
# throttling, indisponibilidade temporária). Cada provider concreto mapeia
# suas exceções de SDK para esta lista.
TRANSIENT_KEYWORDS = (
    "throttl",
    "timeout",
    "timed out",
    "rate",
    "503",
    "502",
    "500",
    "unavailable",
    "too many requests",
    "connection",
)


@dataclass
class ProviderResult:
    """Resultado padronizado de uma consulta a um único cloud."""

    cloud: str                       # "aws" | "oci" | "gcp"
    answer: str | None = None        # texto da resposta do modelo
    model: str | None = None         # nome/ID do modelo usado
    latency_ms: float = 0.0          # latência ponta-a-ponta em milissegundos
    tokens: int = 0                  # total de tokens (input + output) estimado
    cost_usd: float = 0.0            # custo estimado da chamada em USD
    error: str | None = None         # mensagem de erro (None se sucesso)

    @property
    def ok(self) -> bool:
        """True quando a consulta retornou uma resposta sem erro."""
        return self.error is None and self.answer is not None

    def to_dict(self) -> dict[str, Any]:
        """Serializa para JSON (usado nas respostas da API)."""
        return asdict(self)


class BaseProvider(abc.ABC):
    """
    Classe base para todos os providers de cloud.

    Subclasses implementam apenas `_invoke()` — a lógica específica do SDK.
    A base cuida de: medição de latência, timeout de 30s, 2 retentativas em
    erros transitórios e o contrato de "nunca levantar exceção".
    """

    name: str = "base"               # identificador do cloud (sobrescrito)
    default_model: str = "unknown"   # modelo padrão (sobrescrito)

    # Preços em USD por 1 milhão de tokens (input, output). Sobrescrito por cloud.
    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0

    def __init__(self, timeout: float = 30.0, max_retries: int = 2) -> None:
        self.timeout = timeout
        self.max_retries = max_retries

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    async def query(self, prompt: str, timeout: float | None = None) -> ProviderResult:
        """
        Consulta o modelo do cloud de forma assíncrona.

        Mede a latência, aplica timeout e retenta em erros transitórios.
        NUNCA levanta exceção — falhas viram `error` no ProviderResult.
        """
        effective_timeout = timeout if timeout is not None else self.timeout
        start = time.perf_counter()
        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            try:
                # Cada provider concreto roda seu SDK (potencialmente bloqueante)
                # dentro de _invoke, que protegemos com asyncio.wait_for.
                answer, in_tokens, out_tokens, model = await asyncio.wait_for(
                    self._invoke(prompt), timeout=effective_timeout
                )
                latency_ms = (time.perf_counter() - start) * 1000.0
                tokens = in_tokens + out_tokens
                cost = self._estimate_cost(in_tokens, out_tokens)
                return ProviderResult(
                    cloud=self.name,
                    answer=answer,
                    model=model or self.default_model,
                    latency_ms=round(latency_ms, 1),
                    tokens=tokens,
                    cost_usd=round(cost, 8),
                )
            except asyncio.TimeoutError:
                last_error = f"timeout após {effective_timeout:.0f}s"
                # Timeout é transitório: tenta de novo se ainda houver tentativas.
                if attempt < self.max_retries:
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                break
            except Exception as exc:  # noqa: BLE001 — contrato: nunca propagar
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < self.max_retries and self._is_transient(exc):
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                break

        latency_ms = (time.perf_counter() - start) * 1000.0
        return ProviderResult(
            cloud=self.name,
            model=self.default_model,
            latency_ms=round(latency_ms, 1),
            error=last_error or "erro desconhecido",
        )

    async def health(self) -> bool:
        """
        Verifica rapidamente se o provider está utilizável (config presente).
        Sobrescrito por cloud; por padrão tenta um ping curto.
        """
        return True

    # ------------------------------------------------------------------ #
    # A ser implementado por cada cloud
    # ------------------------------------------------------------------ #
    @abc.abstractmethod
    async def _invoke(self, prompt: str) -> tuple[str, int, int, str]:
        """
        Executa a chamada real ao modelo.

        Retorna: (texto_resposta, tokens_input, tokens_output, nome_modelo)
        Pode levantar exceção — a base captura e converte em erro/retry.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _estimate_cost(self, in_tokens: int, out_tokens: int) -> float:
        """Custo = (tokens_in * preço_in + tokens_out * preço_out) / 1M."""
        return (
            in_tokens * self.price_in_per_mtok
            + out_tokens * self.price_out_per_mtok
        ) / 1_000_000.0

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        """Heurística para decidir se vale retentar com base na mensagem."""
        text = str(exc).lower()
        return any(kw in text for kw in TRANSIENT_KEYWORDS)

    @staticmethod
    def _backoff(attempt: int) -> float:
        """Backoff exponencial simples: 0.5s, 1s, 2s..."""
        return 0.5 * (2 ** attempt)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimativa grosseira de tokens (~4 chars/token) usada quando o SDK
        não devolve contagem de uso. Suficiente para custo aproximado.
        """
        return max(1, len(text) // 4)
