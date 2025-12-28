"""Tests for LLM client."""
import pytest

from edps.config import EdpsConfig
from edps.core.llm import LLMClient


class TestAzureProvider:
    """Tests for Azure provider configuration."""

    def test_client_creation(self):
        """LLMClient can be created with Azure config."""
        config = EdpsConfig()
        config.provider = "azure"
        config.azure.endpoint = "https://test.azure.com"
        config.azure.api_key = "test-key"

        client = LLMClient(config)

        assert client.azure_config.endpoint == "https://test.azure.com"
        assert client.default_model == "claude-sonnet-4-20250514"

    def test_preview_estimates_tokens(self):
        """preview() estimates tokens without API call."""
        config = EdpsConfig()
        config.provider = "azure"
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


class TestVSCodeProvider:
    """Tests for VS Code provider configuration."""

    def test_client_creation(self):
        """LLMClient can be created with VS Code config."""
        config = EdpsConfig()
        config.provider = "vscode"

        client = LLMClient(config)

        assert client.provider == "vscode"
        assert client.default_model == "gpt-5"

    def test_preview_estimates_tokens(self):
        """preview() estimates tokens without API call."""
        config = EdpsConfig()
        config.provider = "vscode"

        client = LLMClient(config)

        preview = client.preview(
            prompt="Summarize this text: " + "word " * 100,
            estimated_output_tokens=500,
        )

        assert preview.input_tokens > 100
        assert preview.estimated_output_tokens == 500
        assert preview.estimated_cost >= 0  # VS Code may have zero cost
        assert preview.model == "gpt-5"


class TestProviderRouting:
    """Tests for provider selection logic."""

    def test_default_provider_is_vscode(self):
        """Default config uses VS Code provider."""
        config = EdpsConfig()
        client = LLMClient(config)

        assert client.provider == "vscode"

    def test_explicit_model_overrides_default(self):
        """Explicit model in preview() overrides provider default."""
        config = EdpsConfig()
        config.provider = "vscode"

        client = LLMClient(config)
        preview = client.preview(
            prompt="Test prompt",
            model="claude-sonnet-4-20250514",
            estimated_output_tokens=100,
        )

        assert preview.model == "claude-sonnet-4-20250514"
