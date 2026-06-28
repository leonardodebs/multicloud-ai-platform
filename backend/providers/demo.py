# -*- coding: utf-8 -*-
"""
Modo DEMO — respostas sintéticas quando não há credenciais de cloud.

Permite que o `docker-compose up` funcione ponta-a-ponta sem nenhuma conta
AWS/OCI/GCP. Cada cloud recebe uma latência simulada distinta para que os
gráficos (LatencyChart, "mais rápido") fiquem realistas na demonstração.
"""

from __future__ import annotations

import asyncio
import random

# Latência base simulada por cloud (ms). Valores distintos para que o modo
# "mais rápido" e o gráfico de barras tenham variação visível.
_DEMO_LATENCY = {
    "aws": (350, 650),
    "oci": (500, 950),
    "gcp": (250, 550),
}

_DISCLAIMER = (
    "[DEMO] Resposta sintética gerada localmente porque não há credenciais "
    "de cloud configuradas. Configure AWS/OCI/GCP (veja .env.example) para "
    "consultar os modelos reais."
)


async def demo_answer(cloud: str, prompt: str, model: str) -> tuple[str, int, int, str]:
    """
    Devolve uma resposta de demonstração no mesmo formato de `_invoke`:
    (texto, tokens_input, tokens_output, modelo).
    """
    lo, hi = _DEMO_LATENCY.get(cloud, (300, 700))
    delay = random.uniform(lo, hi) / 1000.0
    await asyncio.sleep(delay)  # simula a latência de rede da chamada real

    short_prompt = prompt.strip().replace("\n", " ")
    if len(short_prompt) > 120:
        short_prompt = short_prompt[:117] + "..."

    answer = (
        f"{_DISCLAIMER}\n\n"
        f"Pergunta recebida: \"{short_prompt}\"\n\n"
        f"Em produção, o modelo {model} ({cloud.upper()}) responderia aqui com "
        f"uma análise completa. Esta plataforma multicloud consultaria AWS "
        f"Bedrock, OCI GenAI e GCP Vertex AI em paralelo e compararia as "
        f"respostas lado a lado."
    )

    in_tokens = max(1, len(prompt) // 4)
    out_tokens = max(1, len(answer) // 4)
    return answer, in_tokens, out_tokens, model
