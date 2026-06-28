# -*- coding: utf-8 -*-
"""Pacote de providers multicloud (AWS, OCI, GCP)."""

from .base_provider import BaseProvider, ProviderResult
from .aws_provider import AWSProvider
from .oci_provider import OCIProvider
from .gcp_provider import GCPProvider

# Registro de providers disponíveis, indexado pelo identificador do cloud.
PROVIDERS = {
    "aws": AWSProvider,
    "oci": OCIProvider,
    "gcp": GCPProvider,
}

__all__ = [
    "BaseProvider",
    "ProviderResult",
    "AWSProvider",
    "OCIProvider",
    "GCPProvider",
    "PROVIDERS",
]
