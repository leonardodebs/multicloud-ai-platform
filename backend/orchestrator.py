# -*- coding: utf-8 -*-
"""
Orquestrador multicloud.

Coordena consultas paralelas aos providers AWS/OCI/GCP e implementa os três
modos da plataforma:

  - comparar  (query_parallel): consulta todos em paralelo e devolve cada
                                 resposta lado a lado.
  - consenso  (query_consensus): consulta todos e usa o Claude para sintetizar
                                  uma resposta única a partir das três.
  - mais rápido (query_fastest): retorna a PRIMEIRA resposta válida e cancela
                                  as demais (menor latência possível).
"""

from __future__ import annotations

import asyncio

from providers import PROVIDERS, ProviderResult


class Orchestrator:
    """Cria e mantém instâncias dos providers e roteia as consultas."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        # Instancia um provider por cloud uma única vez (reuso de clientes SDK).
        self.providers = {name: cls(timeout=timeout) for name, cls in PROVIDERS.items()}

    def _select(self, clouds: list[str]) -> list[str]:
        """Filtra a lista de clouds para os que de fato existem."""
        return [c for c in clouds if c in self.providers]

    # ------------------------------------------------------------------ #
    # Modo: comparar
    # ------------------------------------------------------------------ #
    async def query_parallel(
        self, clouds: list[str], prompt: str
    ) -> dict[str, ProviderResult]:
        """
        Consulta todos os clouds simultaneamente via asyncio.gather.
        Retorna um dict {cloud: ProviderResult}. Como os providers nunca
        levantam exceção, gather sempre completa.
        """
        selected = self._select(clouds)
        results = await asyncio.gather(
            *(self.providers[c].query(prompt) for c in selected)
        )
        return dict(zip(selected, results))

    # ------------------------------------------------------------------ #
    # Modo: consenso
    # ------------------------------------------------------------------ #
    async def query_consensus(
        self, clouds: list[str], prompt: str
    ) -> tuple[str, dict[str, ProviderResult]]:
        """
        Consulta todos em paralelo e sintetiza uma resposta única com o Claude.
        Devolve (texto_consenso, resultados_individuais).
        """
        results = await self.query_parallel(clouds, prompt)
        consensus = await self._synthesize(prompt, results)
        return consensus, results

    async def _synthesize(
        self, prompt: str, results: dict[str, ProviderResult]
    ) -> str:
        """
        Usa o Claude (AWS Bedrock) para combinar as respostas dos clouds numa
        síntese coerente. Se o provider AWS estiver em modo demo, a própria
        resposta demo do Claude já serve como síntese.
        """
        ok_results = {c: r for c, r in results.items() if r.ok}
        if not ok_results:
            return "Nenhum cloud retornou resposta para sintetizar."

        # Monta um meta-prompt pedindo a síntese das respostas individuais.
        partes = "\n\n".join(
            f"### Resposta do {c.upper()} ({r.model}):\n{r.answer}"
            for c, r in ok_results.items()
        )
        meta_prompt = (
            "Você é um sintetizador. Abaixo estão respostas de diferentes "
            "modelos de IA para a mesma pergunta. Produza UMA resposta única, "
            "coerente e concisa, combinando os melhores pontos de cada uma e "
            "resolvendo eventuais contradições.\n\n"
            f"## Pergunta original:\n{prompt}\n\n"
            f"## Respostas dos modelos:\n{partes}\n\n"
            "## Síntese final:"
        )

        # O sintetizador é sempre o Claude na AWS (melhor para esta tarefa).
        synth = await self.providers["aws"].query(meta_prompt)
        if synth.ok and synth.answer:
            return synth.answer
        # Fallback: concatena de forma simples se a síntese falhar.
        return "Consenso (fallback): " + " | ".join(
            r.answer.split("\n")[0] for r in ok_results.values() if r.answer
        )

    # ------------------------------------------------------------------ #
    # Modo: mais rápido
    # ------------------------------------------------------------------ #
    async def query_fastest(self, clouds: list[str], prompt: str) -> ProviderResult:
        """
        Dispara todos os clouds e retorna a PRIMEIRA resposta válida,
        cancelando as demais. Reduz a latência ao mínimo entre os clouds.
        """
        selected = self._select(clouds)
        if not selected:
            return ProviderResult(cloud="none", error="nenhum cloud selecionado")

        tasks = {
            asyncio.create_task(self.providers[c].query(prompt)): c for c in selected
        }
        pending = set(tasks.keys())
        last_result: ProviderResult | None = None

        try:
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    result = task.result()
                    last_result = result
                    if result.ok:
                        # Achou um vencedor: cancela o restante e retorna.
                        for p in pending:
                            p.cancel()
                        return result
            # Ninguém respondeu com sucesso: devolve o último (com erro).
            return last_result or ProviderResult(
                cloud="none", error="nenhuma resposta"
            )
        finally:
            # Garante que tarefas canceladas sejam aguardadas (limpeza).
            for p in pending:
                p.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

    # ------------------------------------------------------------------ #
    # Custos e saúde
    # ------------------------------------------------------------------ #
    @staticmethod
    def calculate_total_cost(results: dict[str, ProviderResult]) -> float:
        """Soma o custo estimado de todos os resultados."""
        return round(sum(r.cost_usd for r in results.values()), 8)

    async def health(self) -> dict[str, str]:
        """Retorna 'ok'/'error' por cloud para o endpoint /health."""
        async def check(name: str) -> tuple[str, str]:
            try:
                ok = await self.providers[name].health()
                return name, "ok" if ok else "error"
            except Exception:  # noqa: BLE001
                return name, "error"

        pairs = await asyncio.gather(*(check(n) for n in self.providers))
        return dict(pairs)

    def models(self) -> dict[str, list[str]]:
        """Lista os modelos por cloud para o endpoint /models."""
        return {name: [p.default_model] for name, p in self.providers.items()}
