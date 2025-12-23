"""Tests for progress detection module."""
from pathlib import Path

import pytest

from edps.progress import check_recall_completion


FIXTURES = Path(__file__).parent / "fixtures"


class TestCheckRecallCompletion:
    """Tests for check_recall_completion function."""

    def test_template_is_incomplete(self):
        """Unfilled template should be incomplete."""
        result = check_recall_completion(FIXTURES / "recall_template.md")
        assert result.is_complete is False
        assert result.score is None

    def test_filled_recall_is_complete(self):
        """Properly filled recall should be complete with score."""
        result = check_recall_completion(FIXTURES / "recall_complete.md")
        assert result.is_complete is True
        assert result.score == 4

    def test_partial_recall_is_incomplete(self):
        """Recall with remaining placeholders should be incomplete."""
        result = check_recall_completion(FIXTURES / "recall_partial.md")
        assert result.is_complete is False
        assert result.score == 3  # Score still extractable even if incomplete
