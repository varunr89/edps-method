"""Tests for state detection."""
import tempfile
from pathlib import Path

import yaml

from edps.core.state import detect_book_state, BookState


def test_detect_state_no_sections():
    """No sections.yaml means not ingested."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir) / "test-book"
        book_dir.mkdir()

        state = detect_book_state(book_dir)

        assert state.ingested is False
        assert state.total_sections == 0


def test_detect_state_with_sections():
    """With sections.yaml, counts what's generated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir) / "test-book"
        book_dir.mkdir()

        # Create sections.yaml
        (book_dir / "sections.yaml").write_text(yaml.dump({
            "sections": [
                {"id": "001", "title": "First"},
                {"id": "002", "title": "Second"},
                {"id": "003", "title": "Third"},
            ]
        }))

        # Create some generated files
        section_001 = book_dir / "sections" / "001"
        section_001.mkdir(parents=True)
        (section_001 / "source.txt").write_text("content")
        (section_001 / "summary.md").write_text("summary")

        section_002 = book_dir / "sections" / "002"
        section_002.mkdir(parents=True)
        (section_002 / "source.txt").write_text("content")

        state = detect_book_state(book_dir)

        assert state.ingested is True
        assert state.total_sections == 3
        assert state.summaries_done == 1
        assert state.podcasts_done == 0
