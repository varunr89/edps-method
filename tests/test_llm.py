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


def test_preview_estimates_tokens():
    """preview() estimates tokens without API call."""
    config = EdpsConfig()
    config.azure.endpoint = "https://test.azure.com"
    config.azure.api_key = "test-key"

    client = LLMClient(config)

    preview = client.preview(
        prompt="Summarize this text: " + "word " * 100,
        estimated_output_tokens=500,
    )

    assert preview.input_tokens > 100
    assert preview.estimated_output_tokens == 500
    assert preview.estimated_cost > 0
    assert preview.model == "claude-sonnet-4-20250514"
