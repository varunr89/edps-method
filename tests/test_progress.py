"""Tests for progress detection module."""
from pathlib import Path

import pytest

from edps.progress import check_recall_completion, check_quiz_completion, QuizResult, check_section_completion, SectionStatus


FIXTURES = Path(__file__).parent / "fixtures"
SECTIONS_FIXTURES = FIXTURES / "sections"


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


class TestCheckQuizCompletion:
    """Tests for check_quiz_completion function."""

    def test_template_is_incomplete(self):
        """Unfilled template should be incomplete."""
        result = check_quiz_completion(FIXTURES / "quiz_template.md")
        assert result.is_complete is False
        assert result.score is None

    def test_filled_quiz_is_complete(self):
        """Properly filled quiz should be complete with score."""
        result = check_quiz_completion(FIXTURES / "quiz_complete.md")
        assert result.is_complete is True
        assert result.score == 7

    def test_partial_quiz_is_incomplete(self):
        """Quiz with empty answers or no total should be incomplete."""
        result = check_quiz_completion(FIXTURES / "quiz_partial.md")
        assert result.is_complete is False
        assert result.score is None  # No total filled in


class TestCheckSectionCompletion:
    """Tests for check_section_completion function."""

    def test_complete_section(self):
        """Section with both recall and quiz complete is complete."""
        result = check_section_completion(SECTIONS_FIXTURES / "complete")
        assert result.is_complete is True
        assert result.recall_score == 4
        assert result.quiz_score == 7

    def test_incomplete_section(self):
        """Section with incomplete quiz is not complete."""
        result = check_section_completion(SECTIONS_FIXTURES / "incomplete")
        assert result.is_complete is False
        assert result.recall_score == 4  # Recall is complete
        assert result.quiz_score is None  # Quiz has no total

    def test_missing_files(self):
        """Section with missing files is not complete."""
        result = check_section_completion(FIXTURES / "nonexistent")
        assert result.is_complete is False
        assert result.recall_score is None
        assert result.quiz_score is None
