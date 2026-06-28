# -*- coding: utf-8 -*-
"""
Provider OCI — Oracle Cloud Infrastructure Generative AI.

Usa o SDK `oci.generative_ai_inference` com o modelo Cohere Command (R).
O SDK é síncrono, então a chamada roda em thread executor.

Autenticação: arquivo de config OCI (~/.oci/config) ou variáveis de ambiente.
Sem credenciais → MODO DEMO, mantendo o docker-compose funcional offline.
"""

from __future__ import annotations

import asyncio
import os

from .base_provider import BaseProvider
from .demo import demo_answer


class OCIProvider(BaseProvider):
    name = "oci"
    default_model = "cohere.command-r-08-2024"

    # Preços de referência do Cohere Command R na OCI (USD por 1M tokens).
    price_in_per_mtok = 0.50
    price_out_per_mtok = 1.50

    def __init__(self, timeout: float = 30.0, max_retries: int = 2) -> None:
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.model_id = os.getenv("OCI_MODEL_ID", self.default_model)
        self.compartment_id = os.getenv("OCI_COMPARTMENT_ID", "")
        self.region = os.getenv("OCI_REGION", "us-chicago-1")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
        self._client = None
        self._demo = False
        self._init_client()

    def _init_client(self) -> None:
        """Inicializa o cliente OCI; cai em modo demo se faltar config."""
        if os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes"):
            self._demo = True
            return
        if not self.compartment_id:
            # Sem compartment não há como rotear a chamada → demo.
            self._demo = True
            return
        try:
            import oci  # import tardio

            config = oci.config.from_file(
                file_location=os.getenv("OCI_CONFIG_FILE", "~/.oci/config"),
                profile_name=os.getenv("OCI_PROFILE", "DEFAULT"),
            )
            endpoint = (
                f"https://inference.generativeai.{self.region}.oci.oraclecloud.com"
            )
            self._client = oci.generative_ai_inference.GenerativeAiInferenceClient(
                config=config,
                service_endpoint=endpoint,
                timeout=(10, self.timeout),
            )
        except Exception:  # noqa: BLE001 — falha de setup → demo
            self._demo = True
            self._client = None

    async def _invoke(self, prompt: str) -> tuple[str, int, int, str]:
        if self._demo or self._client is None:
            return await demo_answer(self.name, prompt, self.default_model)

        def _call() -> object:
            import oci

            chat_request = oci.generative_ai_inference.models.CohereChatRequest(
                message=prompt,
                max_tokens=self.max_tokens,
                temperature=0.3,
            )
            detail = oci.generative_ai_inference.models.ChatDetails(
                compartment_id=self.compartment_id,
                serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                    model_id=self.model_id
                ),
                chat_request=chat_request,
            )
            return self._client.chat(detail)

        resp = await asyncio.to_thread(_call)
        chat_response = resp.data.chat_response
        answer = (getattr(chat_response, "text", "") or "").strip()

        # OCI nem sempre devolve contagem de tokens; estimamos quando ausente.
        in_tokens = self.estimate_tokens(prompt)
        out_tokens = self.estimate_tokens(answer)
        return answer, in_tokens, out_tokens, self.model_id

    async def health(self) -> bool:
        return True
