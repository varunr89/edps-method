"""Tests for generate command."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml
from typer.testing import CliRunner

from edps.cli import app
from edps.core.llm import LLMResponse


runner = CliRunner()


def test_generate_creates_summary(monkeypatch):
    """edps generate creates summary.md for a section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup book structure
        book_dir = tmpdir / "books" / "test-book"
        section_dir = book_dir / "sections" / "001"
        section_dir.mkdir(parents=True)

        # Create sections.yaml
        (book_dir / "sections.yaml").write_text(yaml.dump({
            "sections": [{
                "id": "001",
                "title": "Test Chapter",
                "location": "Chapter 1",
                "word_count": 500,
            }]
        }))

        # Create meta.yaml
        (book_dir / "meta.yaml").write_text(yaml.dump({
            "title": "Test Book",
            "author": "Test Author",
        }))

        # Create source.txt
        (section_dir / "source.txt").write_text("This is the chapter content.")

        # Create config
        config_dir = tmpdir / ".edps"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(yaml.dump({
            "azure": {
                "endpoint": "https://test.azure.com",
                "api_key": "test-key",
            }
        }))

        # Mock LLM response
        mock_response = LLMResponse(
            content="# Section 001: Test Chapter\n\n## TLDR\n\nThis is a test summary.",
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
            model="claude-sonnet-4-20250514",
        )

        with patch("edps.commands.generate.LLMClient") as MockClient:
            mock_client = MagicMock()
            mock_client.preview.return_value = MagicMock(
                input_tokens=100,
                estimated_output_tokens=500,
                estimated_cost=0.01,
                model="claude-sonnet-4-20250514",
                prompt="test prompt",
            )
            mock_client.complete.return_value = mock_response
            mock_client.default_model = "claude-sonnet-4-20250514"
            MockClient.return_value = mock_client

            result = runner.invoke(app, [
                "generate", "test-book", "001",
                "--books-dir", str(tmpdir / "books"),
                "--config-path", str(config_dir / "config.yaml"),
                "--yes",
                "--type", "summary",
            ])

        assert result.exit_code == 0, result.output

        summary_path = section_dir / "summary.md"
        assert summary_path.exists()
        assert "TLDR" in summary_path.read_text()
