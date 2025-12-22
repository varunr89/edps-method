"""Tests for template command."""
import tempfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from edps.cli import app


runner = CliRunner()


def test_template_creates_recall_md():
    """edps template creates recall.md for sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup book structure
        book_dir = tmpdir / "books" / "test-book"
        section_dir = book_dir / "sections" / "001"
        section_dir.mkdir(parents=True)

        (book_dir / "sections.yaml").write_text(yaml.dump({
            "sections": [{"id": "001", "title": "Test Chapter"}]
        }))

        result = runner.invoke(app, [
            "template", "test-book",
            "--books-dir", str(tmpdir / "books"),
        ])

        assert result.exit_code == 0

        recall_path = section_dir / "recall.md"
        assert recall_path.exists()
        assert "<!-- TEMPLATE" in recall_path.read_text()
        assert "From Memory" in recall_path.read_text()
