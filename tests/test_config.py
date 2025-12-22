"""Tests for config module."""
import tempfile
from pathlib import Path

import pytest
import yaml

from edps.config import load_config, EdpsConfig


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
