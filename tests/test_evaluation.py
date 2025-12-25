"""Tests for AI evaluation module."""
from unittest.mock import MagicMock, patch
from edps.evaluation import RecallFeedback, QuizFeedback, AnswerFeedback, parse_recall_content, parse_quiz_content


class TestDataclasses:
    """Tests for evaluation dataclasses."""

    def test_recall_feedback_creation(self):
        """RecallFeedback dataclass should hold evaluation results."""
        feedback = RecallFeedback(
            points=[
                AnswerFeedback(label="Main claim", correct=True, note="Correct"),
                AnswerFeedback(label="Mechanism", correct=False, note="Missed X"),
            ],
            one_sentence_ok=True,
            one_sentence_note="Strong summary",
            score=4,
            reasoning="Good recall overall",
        )
        assert feedback.score == 4
        assert len(feedback.points) == 2
        assert feedback.points[1].correct is False

    def test_quiz_feedback_creation(self):
        """QuizFeedback dataclass should hold quiz evaluation."""
        feedback = QuizFeedback(
            answers=[
                AnswerFeedback(label="Q1", correct=True, score=1.0, note="Correct"),
                AnswerFeedback(label="Q2", correct=False, score=0.5, note="Partial"),
            ],
            total_score=7.5,
            reasoning="Strong comprehension",
        )
        assert feedback.total_score == 7.5
        assert feedback.answers[1].score == 0.5


class TestParseRecallContent:
    """Tests for parsing recall.md content."""

    def test_extracts_memory_points(self):
        """Should extract numbered points from memory section."""
        content = '''## From Memory (before re-reading)

*Write these BEFORE looking at source or summary:*

1. Division of labor is critical.
2. Three causes of productivity.
3. Pin factory example.
'''
        result = parse_recall_content(content)
        assert len(result["memory_points"]) == 3
        assert "Division of labor" in result["memory_points"][0]

    def test_extracts_one_sentence(self):
        """Should extract one sentence summary."""
        content = '''## One Sentence I'd Tell Someone

Division of labor drives economic growth.
'''
        result = parse_recall_content(content)
        assert "Division of labor" in result["one_sentence"]

    def test_handles_missing_sections(self):
        """Should handle missing sections gracefully."""
        content = "# Recall\n\nSome content"
        result = parse_recall_content(content)
        assert result["memory_points"] == []
        assert result["one_sentence"] == ""


class TestParseQuizContent:
    """Tests for parsing quiz.md content."""

    def test_extracts_questions_and_answers(self):
        """Should extract all Q&A pairs with metadata."""
        content = '''### 1. Main Claim

What is the primary cause?

**Answer:** Division of labor.

---

### 2. Mechanism

What are the three causes?

**Answer:** Dexterity, time savings, machinery.
'''
        result = parse_quiz_content(content)
        assert len(result["qa_pairs"]) == 2
        assert result["qa_pairs"][0]["number"] == "1"
        assert result["qa_pairs"][0]["title"] == "Main Claim"
        assert "Division of labor" in result["qa_pairs"][0]["answer"]

    def test_handles_multiline_answers(self):
        """Should handle answers spanning multiple lines."""
        content = '''### 8. Modern Connection

How does this connect?

**Answer:** This connects because of X.
And also Y.
Furthermore Z.

---
'''
        result = parse_quiz_content(content)
        assert "X" in result["qa_pairs"][0]["answer"]
        assert "Z" in result["qa_pairs"][0]["answer"]


class TestBuildEvaluationPrompt:
    """Tests for building evaluation prompts."""

    def test_includes_source_text(self):
        """Prompt should include the source text."""
        from edps.evaluation import build_evaluation_prompt

        source = "Division of labor increases productivity through specialization."
        recall = "## From Memory\n\n1. Specialization helps.\n\n## One Sentence\n\nLabor division is key."
        quiz = "### 1. Main\n\nWhat helps?\n\n**Answer:** Specialization"

        prompt = build_evaluation_prompt(source, recall, quiz)
        assert "Division of labor" in prompt
        assert source in prompt

    def test_includes_user_answers(self):
        """Prompt should include recall points, summary, and quiz answers."""
        from edps.evaluation import build_evaluation_prompt

        source = "Source text here"
        recall = "## From Memory (before re-reading)\n\n*Instructions*\n\n1. Point one.\n2. Point two.\n\n## One Sentence\n\nMy summary."
        quiz = "### 1. Q1\n\nQuestion?\n\n**Answer:** My answer"

        prompt = build_evaluation_prompt(source, recall, quiz)
        assert "Point one" in prompt
        assert "Point two" in prompt
        assert "My summary" in prompt
        assert "My answer" in prompt

    def test_requests_json_output(self):
        """Prompt should request JSON formatted response."""
        from edps.evaluation import build_evaluation_prompt

        source = "Test"
        recall = "## From Memory\n\n1. Test\n\n## One Sentence\n\nTest"
        quiz = "### 1. T\n\nT?\n\n**Answer:** T"

        prompt = build_evaluation_prompt(source, recall, quiz)
        assert "json" in prompt.lower() or "JSON" in prompt
        assert "{" in prompt or "schema" in prompt.lower()


class TestParseEvaluationResponse:
    """Tests for parsing LLM evaluation responses."""

    def test_parses_valid_json(self):
        """Should parse clean JSON response into feedback objects."""
        from edps.evaluation import parse_evaluation_response

        response = """{
  "recall": {
    "points": [
      {"label": "Division of labor", "correct": true, "note": "Good"},
      {"label": "Pin factory", "correct": false, "note": "Missed details"}
    ],
    "one_sentence_ok": true,
    "one_sentence_note": "Clear summary",
    "score": 4,
    "reasoning": "Strong recall"
  },
  "quiz": {
    "answers": [
      {"label": "Q1: Main claim", "correct": true, "score": 1.0, "note": "Perfect"},
      {"label": "Q2: Mechanism", "correct": false, "score": 0.5, "note": "Partial"}
    ],
    "total_score": 6.5,
    "reasoning": "Good understanding"
  }
}"""

        recall_fb, quiz_fb = parse_evaluation_response(response)

        assert recall_fb.score == 4
        assert len(recall_fb.points) == 2
        assert recall_fb.points[0].correct is True
        assert recall_fb.points[1].correct is False
        assert recall_fb.one_sentence_ok is True

        assert quiz_fb.total_score == 6.5
        assert len(quiz_fb.answers) == 2
        assert quiz_fb.answers[0].score == 1.0
        assert quiz_fb.answers[1].score == 0.5

    def test_handles_json_in_markdown(self):
        """Should extract JSON from markdown code blocks."""
        from edps.evaluation import parse_evaluation_response

        response = """Here is the evaluation:

```json
{
  "recall": {
    "points": [
      {"label": "Test", "correct": true, "note": "OK"}
    ],
    "one_sentence_ok": true,
    "one_sentence_note": "Good",
    "score": 5,
    "reasoning": "Perfect"
  },
  "quiz": {
    "answers": [
      {"label": "Q1", "correct": true, "score": 1.0, "note": "Correct"}
    ],
    "total_score": 8.0,
    "reasoning": "Perfect score"
  }
}
```

Additional commentary here."""

        recall_fb, quiz_fb = parse_evaluation_response(response)

        assert recall_fb.score == 5
        assert quiz_fb.total_score == 8.0


class TestFormatFeedback:
    """Tests for formatting feedback as markdown."""

    def test_recall_feedback_format(self):
        """Should format recall feedback as markdown table."""
        from edps.evaluation import format_recall_feedback, RecallFeedback, AnswerFeedback

        feedback = RecallFeedback(
            points=[
                AnswerFeedback(label="Labor division", correct=True, note="Accurate"),
                AnswerFeedback(label="Pin factory", correct=False, note="Missing detail"),
            ],
            one_sentence_ok=True,
            one_sentence_note="Clear and concise",
            score=4,
            reasoning="Good overall"
        )

        markdown = format_recall_feedback(feedback, "2024-01-15", "section-001/source.md")

        # Should have header
        assert "## AI Feedback" in markdown
        assert "2024-01-15" in markdown
        assert "section-001/source.md" in markdown

        # Should have table
        assert "| Point | Status | Feedback |" in markdown or "Point" in markdown and "Status" in markdown

        # Should have checkmarks/warnings
        assert "✓" in markdown or "✅" in markdown
        assert "⚠" in markdown or "⚠️" in markdown

        # Should have content
        assert "Labor division" in markdown
        assert "Accurate" in markdown
        assert "Pin factory" in markdown
        assert "score" in markdown.lower() or "4" in markdown

    def test_quiz_feedback_format(self):
        """Should format quiz feedback as markdown table."""
        from edps.evaluation import format_quiz_feedback, QuizFeedback, AnswerFeedback

        feedback = QuizFeedback(
            answers=[
                AnswerFeedback(label="Q1: Main claim", correct=True, score=1.0, note="Perfect"),
                AnswerFeedback(label="Q2: Mechanism", correct=False, score=0.5, note="Partial credit"),
            ],
            total_score=7.5,
            reasoning="Strong comprehension"
        )

        markdown = format_quiz_feedback(feedback, "2024-01-15", "section-001/source.md")

        # Should have header
        assert "## AI Feedback" in markdown
        assert "2024-01-15" in markdown
        assert "section-001/source.md" in markdown

        # Should have table
        assert "| Question | Status | Score | Feedback |" in markdown or ("Question" in markdown and "Score" in markdown)

        # Should have checkmarks/warnings
        assert "✓" in markdown or "✅" in markdown
        assert "⚠" in markdown or "⚠️" in markdown

        # Should have content
        assert "Q1" in markdown or "Main claim" in markdown
        assert "Q2" in markdown or "Mechanism" in markdown
        assert "7.5" in markdown or "total" in markdown.lower()


class TestEvaluateSection:
    """Tests for evaluate_section main function."""

    def test_reads_required_files(self, tmp_path):
        """Should read source, recall, and quiz files."""
        from edps.evaluation import evaluate_section

        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)
        (section / "EDPS-test-001.txt").write_text("Source content")
        (section / "recall.md").write_text("## From Memory\n\n1. Point one\n\n## One Sentence\n\nSummary")
        (section / "quiz.md").write_text("### 1. Q1\n\nQuestion?\n\n**Answer:** Answer here")

        with patch("edps.core.llm.LLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.complete.return_value.content = '{"recall": {"points": [], "one_sentence_ok": true, "one_sentence_note": "", "score": 4, "reasoning": ""}, "quiz": {"answers": [], "total_score": 7, "reasoning": ""}}'
            mock_client.return_value = mock_instance
            result = evaluate_section(section, "test", "001")
            assert result is not None
            assert mock_instance.complete.called

    def test_appends_feedback_to_files(self, tmp_path):
        """Should append AI feedback to recall.md and quiz.md."""
        from edps.evaluation import evaluate_section

        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)
        (section / "EDPS-test-001.txt").write_text("Source")
        (section / "recall.md").write_text("# Recall\n\n## From Memory\n\n1. Point\n\n## One Sentence\n\nSum")
        (section / "quiz.md").write_text("### 1. Q1\n\nQ?\n\n**Answer:** A")

        with patch("edps.core.llm.LLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.complete.return_value.content = '{"recall": {"points": [{"label": "P1", "correct": true, "note": "OK"}], "one_sentence_ok": true, "one_sentence_note": "Good", "score": 4, "reasoning": "Good"}, "quiz": {"answers": [{"label": "Q1", "correct": true, "score": 1.0, "note": "OK"}], "total_score": 7, "reasoning": "Good"}}'
            mock_client.return_value = mock_instance
            evaluate_section(section, "test", "001")
            recall_content = (section / "recall.md").read_text()
            quiz_content = (section / "quiz.md").read_text()
            assert "## AI Feedback" in recall_content
            assert "## AI Feedback" in quiz_content

    def test_raises_error_if_source_missing(self, tmp_path):
        """Should raise FileNotFoundError if source file doesn't exist."""
        from edps.evaluation import evaluate_section
        import pytest

        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)
        (section / "recall.md").write_text("## From Memory\n\n1. Point\n\n## One Sentence\n\nSum")
        (section / "quiz.md").write_text("### 1. Q1\n\nQ?\n\n**Answer:** A")

        with pytest.raises(FileNotFoundError):
            evaluate_section(section, "test", "001")

    def test_returns_evaluation_result(self, tmp_path):
        """Should return EvaluationResult with scores and feedback."""
        from edps.evaluation import evaluate_section

        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)
        (section / "EDPS-test-001.txt").write_text("Source")
        (section / "recall.md").write_text("## From Memory\n\n1. Point\n\n## One Sentence\n\nSum")
        (section / "quiz.md").write_text("### 1. Q1\n\nQ?\n\n**Answer:** A")

        with patch("edps.core.llm.LLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.complete.return_value.content = '{"recall": {"points": [], "one_sentence_ok": true, "one_sentence_note": "", "score": 4, "reasoning": ""}, "quiz": {"answers": [], "total_score": 7.5, "reasoning": ""}}'
            mock_client.return_value = mock_instance
            result = evaluate_section(section, "test", "001")

            assert result.recall_score == 4
            assert result.quiz_score == 7.5
            assert result.recall_feedback is not None
            assert result.quiz_feedback is not None

    def test_does_not_duplicate_feedback(self, tmp_path):
        """Should not append feedback if it already exists."""
        from edps.evaluation import evaluate_section

        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)
        (section / "EDPS-test-001.txt").write_text("Source")
        (section / "recall.md").write_text("# Recall\n\n## From Memory\n\n1. Point\n\n## One Sentence\n\nSum\n\n---\n\n## AI Feedback\n\nExisting feedback")
        (section / "quiz.md").write_text("### 1. Q1\n\nQ?\n\n**Answer:** A\n\n---\n\n## AI Feedback\n\nExisting feedback")

        with patch("edps.core.llm.LLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.complete.return_value.content = '{"recall": {"points": [], "one_sentence_ok": true, "one_sentence_note": "", "score": 4, "reasoning": ""}, "quiz": {"answers": [], "total_score": 7, "reasoning": ""}}'
            mock_client.return_value = mock_instance
            evaluate_section(section, "test", "001")

            recall_content = (section / "recall.md").read_text()
            quiz_content = (section / "quiz.md").read_text()

            # Should only have one instance of "## AI Feedback"
            assert recall_content.count("## AI Feedback") == 1
            assert quiz_content.count("## AI Feedback") == 1


class TestIntegration:
    """Integration tests for full evaluation flow."""

    def test_full_evaluation_flow(self, tmp_path):
        """Test complete flow from files to feedback."""
        from edps.evaluation import evaluate_section

        book_path = tmp_path / "books" / "test-book"
        section_path = book_path / "sections" / "001"
        section_path.mkdir(parents=True)

        (section_path / "EDPS-test-book-001.txt").write_text(
            "Division of labor increases productivity through three causes: "
            "dexterity, time savings, and machinery invention."
        )
        (section_path / "recall.md").write_text('''# Recall

## From Memory (before re-reading)

1. Division of labor increases productivity
2. Three causes explain this improvement

## One Sentence I'd Tell Someone

Division of labor is key to productivity.
''')
        (section_path / "quiz.md").write_text('''# Quiz

### 1. Main Claim

What increases productivity?

**Answer:** Division of labor
''')
        (book_path / "progress.yaml").write_text("completed_sections: []\nquiz_scores: {}\nrecall_scores: {}\nstats: {}")

        with patch("edps.core.llm.LLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.complete.return_value.content = '''```json
{
  "recall": {
    "points": [
      {"label": "Productivity claim", "correct": true, "note": "Correct"},
      {"label": "Three causes", "correct": true, "note": "Correct"}
    ],
    "one_sentence_ok": true,
    "one_sentence_note": "Good summary",
    "score": 5,
    "reasoning": "Excellent recall"
  },
  "quiz": {
    "answers": [
      {"label": "Q1", "correct": true, "score": 1.0, "note": "Correct"}
    ],
    "total_score": 8,
    "reasoning": "Perfect"
  }
}
```'''
            mock_client.return_value = mock_instance

            result = evaluate_section(section_path, "test-book", "001")

            assert result.recall_score == 5
            assert result.quiz_score == 8

            recall_content = (section_path / "recall.md").read_text()
            quiz_content = (section_path / "quiz.md").read_text()

            assert "## AI Feedback" in recall_content
            assert "**Overall Score:** 5/5" in recall_content
            assert "## AI Feedback" in quiz_content
            assert "**Total Score:** 8/8" in quiz_content
