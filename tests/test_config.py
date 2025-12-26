"""Tests for config module."""
import tempfile
from pathlib import Path

import pytest
import yaml

from edps.config import load_config, save_config, EdpsConfig


def test_load_config_from_file():
    """Config loads from YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(yaml.dump({
            "azure": {
                "endpoint": "https://test.azure.com",
                "api_key": "test-key",
                "model": "claude-sonnet-4-20250514",
            },
            "defaults": {
                "temperature": 0.3,
                "confirm_before_call": True,
            }
        }))

        config = load_config(config_path)

        assert config.azure.endpoint == "https://test.azure.com"
        assert config.azure.api_key == "test-key"
        assert config.azure.model == "claude-sonnet-4-20250514"
        assert config.defaults.temperature == 0.3
        assert config.defaults.confirm_before_call is True


def test_config_resolves_env_vars(monkeypatch):
    """Config resolves ${ENV_VAR} syntax."""
    monkeypatch.setenv("AZURE_AI_API_KEY", "secret-from-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(yaml.dump({
            "azure": {
                "endpoint": "https://test.azure.com",
                "api_key": "${AZURE_AI_API_KEY}",
            }
        }))

        config = load_config(config_path)

        assert config.azure.api_key == "secret-from-env"


def test_save_config_creates_file():
    """save_config writes YAML to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        config = EdpsConfig()
        config.azure.endpoint = "https://my-endpoint.azure.com"
        config.azure.api_key = "my-api-key"

        save_config(config, config_path)

        assert config_path.exists()
        loaded = yaml.safe_load(config_path.read_text())
        assert loaded["azure"]["endpoint"] == "https://my-endpoint.azure.com"


def test_council_resolves_models_from_roles():
    """Council resolves member_roles to actual model names."""
    from edps.config import CouncilConfig, ModelsConfig

    models = ModelsConfig(
        summary="gemini-3-pro",
        quiz="claude-sonnet-4.5",
        evaluation="gpt-5",
    )
    council = CouncilConfig(
        member_roles=["summary", "quiz", "evaluation"],
        chair_role="evaluation",
    )

    resolved = council.resolve_models(models)
    chair = council.resolve_chair(models)

    assert resolved == ["gemini-3-pro", "claude-sonnet-4.5", "gpt-5"]
    assert chair == "gpt-5"


def test_council_deduplicates_models():
    """Council deduplicates when multiple roles use same model."""
    from edps.config import CouncilConfig, ModelsConfig

    # All roles use the same model
    models = ModelsConfig(
        summary="claude-opus-4-5",
        quiz="claude-opus-4-5",
        evaluation="claude-opus-4-5",
    )
    council = CouncilConfig(
        member_roles=["summary", "quiz", "evaluation"],
        chair_role="evaluation",
    )

    resolved = council.resolve_models(models)

    # Should dedupe to single model
    assert resolved == ["claude-opus-4-5"]
