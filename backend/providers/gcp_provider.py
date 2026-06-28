# -*- coding: utf-8 -*-
"""
Provider GCP — Vertex AI, Gemini 1.5 Flash.

Usa `vertexai.generative_models.GenerativeModel`. O SDK é síncrono, então a
chamada roda em thread executor.

Autenticação: Application Default Credentials (ADC) via
GOOGLE_APPLICATION_CREDENTIALS ou metadata server. Sem credencial/projeto →
MODO DEMO, mantendo o docker-compose funcional offline.
"""

from __future__ import annotations

import asyncio
import os

from .base_provider import BaseProvider
from .demo import demo_answer


class GCPProvider(BaseProvider):
    name = "gcp"
    default_model = "gemini-1.5-flash"

    # Preços de referência do Gemini 1.5 Flash (USD por 1M tokens).
    price_in_per_mtok = 0.075
    price_out_per_mtok = 0.30

    def __init__(self, timeout: float = 30.0, max_retries: int = 2) -> None:
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.model_id = os.getenv("GCP_MODEL_ID", self.default_model)
        self.project = os.getenv("GCP_PROJECT_ID", "")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
        self._model = None
        self._demo = False
        self._init_client()

    def _init_client(self) -> None:
        """Inicializa o modelo Vertex AI; cai em modo demo se faltar config."""
        if os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes"):
            self._demo = True
            return
        if not self.project:
            # Sem projeto GCP não há como inicializar o Vertex → demo.
            self._demo = True
            return
        try:
            import vertexai  # import tardio
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project, location=self.location)
            self._model = GenerativeModel(self.model_id)
        except Exception:  # noqa: BLE001 — falha de setup → demo
            self._demo = True
            self._model = None

    async def _invoke(self, prompt: str) -> tuple[str, int, int, str]:
        if self._demo or self._model is None:
            return await demo_answer(self.name, prompt, self.default_model)

        def _call() -> object:
            from vertexai.generative_models import GenerationConfig

            return self._model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=0.3,
                ),
            )

        resp = await asyncio.to_thread(_call)
        answer = (getattr(resp, "text", "") or "").strip()

        # Vertex devolve usage_metadata com contagem de tokens.
        usage = getattr(resp, "usage_metadata", None)
        if usage is not None:
            in_tokens = getattr(usage, "prompt_token_count", 0)
            out_tokens = getattr(usage, "candidates_token_count", 0)
        else:
            in_tokens = self.estimate_tokens(prompt)
            out_tokens = self.estimate_tokens(answer)
        return answer, in_tokens, out_tokens, self.model_id

    async def health(self) -> bool:
        return True
