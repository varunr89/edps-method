"""Tests for init command."""
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from edps.cli import app


runner = CliRunner()


def test_init_creates_config_file(monkeypatch):
    """edps init creates config.yaml in specified directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        result = runner.invoke(app, [
            "init",
            "--config-path", str(config_path),
            "--endpoint", "https://test.azure.com",
            "--api-key", "test-key",
            "--no-test-connection",
        ])

        assert result.exit_code == 0
        assert config_path.exists()
