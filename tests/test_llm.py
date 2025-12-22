"""Tests for LLM client."""
import pytest

from edps.config import EdpsConfig
from edps.core.llm import LLMClient


def test_client_creation():
    """LLMClient can be created with config."""
    config = EdpsConfig()
    config.azure.endpoint = "https://test.azure.com"
    config.azure.api_key = "test-key"

    client = LLMClient(config)

    assert client.endpoint == "https://test.azure.com"
    assert client.default_model == "claude-sonnet-4-20250514"
