# -*- coding: utf-8 -*-
"""
Provider AWS — Amazon Bedrock, Claude Haiku 4.5 via inference profile.

Usa boto3 `bedrock-runtime` com o formato de mensagens da Anthropic
(anthropic_version + messages). boto3 é síncrono, então a chamada roda em
thread executor para não travar o event loop.

Autenticação: cadeia padrão do boto3 (credenciais do ambiente, perfil, ou
IAM role da task ECS). Se nenhuma credencial estiver disponível, o provider
entra em MODO DEMO e devolve uma resposta sintética — assim o
`docker-compose up` funciona ponta-a-ponta sem conta AWS.
"""

from __future__ import annotations

import asyncio
import json
import os

from .base_provider import BaseProvider
from .demo import demo_answer


class AWSProvider(BaseProvider):
    name = "aws"
    # Inference profile cross-region para o Claude Haiku 4.5 no Bedrock.
    default_model = "us.anthropic.claude-haiku-4-5"

    # Preços de referência do Claude Haiku 4.5 (USD por 1M tokens).
    price_in_per_mtok = 1.00
    price_out_per_mtok = 5.00

    def __init__(self, timeout: float = 30.0, max_retries: int = 2) -> None:
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        self.model_id = os.getenv("AWS_BEDROCK_MODEL_ID", self.default_model)
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
        self._client = None
        self._demo = False
        self._init_client()

    def _init_client(self) -> None:
        """Cria o cliente boto3; cai em modo demo se faltar config/credencial."""
        if os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes"):
            self._demo = True
            return
        try:
            import boto3  # import tardio: nem sempre necessário (modo demo)
            from botocore.config import Config

            cfg = Config(
                region_name=self.region,
                retries={"max_attempts": 0},  # retries são tratados pela base
                read_timeout=self.timeout,
                connect_timeout=10,
            )
            self._client = boto3.client("bedrock-runtime", config=cfg)
            # Se não há credenciais resolvíveis, melhor entrar em demo.
            session = boto3.session.Session()
            if session.get_credentials() is None:
                self._demo = True
                self._client = None
        except Exception:  # noqa: BLE001 — qualquer falha de setup → demo
            self._demo = True
            self._client = None

    async def _invoke(self, prompt: str) -> tuple[str, int, int, str]:
        if self._demo or self._client is None:
            return await demo_answer(self.name, prompt, self.default_model)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        # boto3 é bloqueante → roda em thread para preservar a concorrência.
        def _call() -> dict:
            resp = self._client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            return json.loads(resp["body"].read())

        payload = await asyncio.to_thread(_call)

        # Extrai o texto dos blocos de conteúdo do formato Anthropic.
        answer = "".join(
            block.get("text", "")
            for block in payload.get("content", [])
            if block.get("type") == "text"
        ).strip()

        usage = payload.get("usage", {})
        in_tokens = usage.get("input_tokens", self.estimate_tokens(prompt))
        out_tokens = usage.get("output_tokens", self.estimate_tokens(answer))
        return answer, in_tokens, out_tokens, self.model_id

    async def health(self) -> bool:
        # Em modo demo sempre saudável; com cliente real, basta estar configurado.
        return True
