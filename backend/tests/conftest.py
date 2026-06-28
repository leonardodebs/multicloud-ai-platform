# -*- coding: utf-8 -*-
"""Fixtures e mocks compartilhados pelos testes."""

import os
import sys

import pytest

# Garante que o pacote backend (providers, orchestrator, main) seja importável.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Força modo demo para que NENHUM teste dependa de credenciais ou rede.
os.environ["DEMO_MODE"] = "true"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
