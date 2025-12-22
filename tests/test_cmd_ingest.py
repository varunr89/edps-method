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


def test_ingest_creates_source_files(monkeypatch):
    """edps ingest creates source.txt for each section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir = tmpdir / "books_raw"
        raw_dir.mkdir()
        (raw_dir / "test-book.txt").write_text("""
CHAPTER I.
FIRST CHAPTER TITLE.

First chapter content here.

CHAPTER II.
SECOND CHAPTER TITLE.

Second chapter content here.
""")

        books_dir = tmpdir / "books"
        books_dir.mkdir()

        result = runner.invoke(app, [
            "ingest", "test-book",
            "--books-raw", str(raw_dir),
            "--books-dir", str(books_dir),
            "--yes",
        ])

        assert result.exit_code == 0

        # Check source files created
        source_001 = books_dir / "test-book" / "sections" / "001" / "source.txt"
        source_002 = books_dir / "test-book" / "sections" / "002" / "source.txt"

        assert source_001.exists()
        assert source_002.exists()
        assert "First chapter content" in source_001.read_text()


def test_ingest_fails_without_registry_entry():
    """edps ingest fails if slug is not in _registry.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create books_raw with test book
        raw_dir = tmpdir / "books_raw"
        raw_dir.mkdir()
        (raw_dir / "test-book.txt").write_text("""
CHAPTER I.
THE FIRST CHAPTER.

This is the content of the first chapter.
""")

        # Create books directory with registry that doesn't include test-book
        books_dir = tmpdir / "books"
        books_dir.mkdir()
        (books_dir / "_registry.yaml").write_text(yaml.dump({
            "books": [
                {"slug": "other-book", "title": "Other Book"}
            ]
        }))

        # Run ingest - should fail
        result = runner.invoke(app, [
            "ingest", "test-book",
            "--books-raw", str(raw_dir),
            "--books-dir", str(books_dir),
            "--yes",
        ])

        assert result.exit_code == 1
        assert "not found in _registry.yaml" in result.output


def test_ingest_succeeds_with_registry_entry():
    """edps ingest succeeds when slug exists in _registry.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create books_raw with test book
        raw_dir = tmpdir / "books_raw"
        raw_dir.mkdir()
        (raw_dir / "test-book.txt").write_text("""
CHAPTER I.
THE FIRST CHAPTER.

This is the content of the first chapter.
""")

        # Create books directory with registry that includes test-book
        books_dir = tmpdir / "books"
        books_dir.mkdir()
        (books_dir / "_registry.yaml").write_text(yaml.dump({
            "books": [
                {"slug": "test-book", "title": "Test Book", "author": "Test Author"}
            ]
        }))

        # Run ingest - should succeed
        result = runner.invoke(app, [
            "ingest", "test-book",
            "--books-raw", str(raw_dir),
            "--books-dir", str(books_dir),
            "--yes",
        ])

        assert result.exit_code == 0, result.output
        assert (books_dir / "test-book" / "sections.yaml").exists()


def test_ingest_warns_without_registry_file():
    """edps ingest warns but continues if _registry.yaml doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create books_raw with test book
        raw_dir = tmpdir / "books_raw"
        raw_dir.mkdir()
        (raw_dir / "test-book.txt").write_text("""
CHAPTER I.
THE FIRST CHAPTER.

This is the content of the first chapter.
""")

        # Create books directory WITHOUT registry
        books_dir = tmpdir / "books"
        books_dir.mkdir()
        # No _registry.yaml created

        # Run ingest - should warn but continue
        result = runner.invoke(app, [
            "ingest", "test-book",
            "--books-raw", str(raw_dir),
            "--books-dir", str(books_dir),
            "--yes",
        ])

        assert result.exit_code == 0, result.output
        assert "No _registry.yaml found" in result.output
        assert (books_dir / "test-book" / "sections.yaml").exists()
