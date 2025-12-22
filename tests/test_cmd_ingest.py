"""Tests for ingest command."""
import tempfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from edps.cli import app


runner = CliRunner()


def test_ingest_creates_sections_yaml(monkeypatch):
    """edps ingest creates sections.yaml from raw text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create books_raw with test book
        raw_dir = tmpdir / "books_raw"
        raw_dir.mkdir()
        (raw_dir / "test-book.txt").write_text("""
CHAPTER I.
THE FIRST CHAPTER.

This is the content of the first chapter. It contains many words
to make it seem like a real chapter with substantial content.

CHAPTER II.
THE SECOND CHAPTER.

This is the content of the second chapter. Also with enough words
to be considered a reasonable chapter length.
""")

        # Create books directory
        books_dir = tmpdir / "books"
        books_dir.mkdir()

        # Run ingest
        result = runner.invoke(app, [
            "ingest", "test-book",
            "--books-raw", str(raw_dir),
            "--books-dir", str(books_dir),
            "--yes",  # Skip confirmations
        ])

        assert result.exit_code == 0, result.output

        # Check sections.yaml created
        sections_path = books_dir / "test-book" / "sections.yaml"
        assert sections_path.exists()

        sections = yaml.safe_load(sections_path.read_text())
        assert "sections" in sections
        assert len(sections["sections"]) == 2
