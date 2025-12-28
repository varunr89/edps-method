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
        """Should format quiz feedback with per-answer sections."""
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

        # Should have per-answer sections (new expanded format)
        assert "### Per-Answer Analysis" in markdown
        assert "#### Q1: Main claim" in markdown
        assert "#### Q2: Mechanism" in markdown

        # Should have checkmarks/warnings
        assert "✓" in markdown or "✅" in markdown
        assert "⚠" in markdown or "⚠️" in markdown

        # Should have content (fallback to legacy note field)
        assert "Perfect" in markdown
        assert "Partial credit" in markdown
        assert "7.5" in markdown


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


class TestExpandedAnswerFeedback:
    """Tests for expanded answer feedback with accuracy/reasoning/writing."""

    def test_answer_feedback_has_accuracy_field(self):
        """AnswerFeedback should have accuracy analysis."""
        from edps.evaluation import AnswerFeedback
        feedback = AnswerFeedback(
            label="Q1: Main Claim",
            correct=True,
            note="Legacy note",  # keep backward compat
            score=1.0,
            question_id="q1",
            explanation="Legacy note",
            accuracy="Correct—identified propensity to exchange as origin.",
            reasoning="Causal chain is sound.",
            writing="Consider 'propensity' over 'innate need'.",
        )
        assert feedback.question_id == "q1"
        assert feedback.accuracy == "Correct—identified propensity to exchange as origin."
        assert feedback.reasoning == "Causal chain is sound."
        assert feedback.writing == "Consider 'propensity' over 'innate need'."


class TestThematicInsights:
    """Tests for thematic insights dataclass."""

    def test_thematic_insights_creation(self):
        """ThematicInsights should hold cross-answer patterns."""
        from edps.evaluation import ThematicInsights, WritingScores

        writing = WritingScores(precision=3, clarity=4, economy=3, suggestion="Cut 30% without losing meaning.")
        insights = ThematicInsights(
            source_mastery="You grasp the core thesis. Pattern: you sharpen Smith's hedges into certainties.",
            reasoning_quality="Arguments are structurally sound. Push the 'so what' further.",
            writing_craft=writing,
        )
        assert insights.writing_craft.precision == 3
        assert "hedges" in insights.source_mastery


class TestExpandedFeedback:
    """Tests for expanded feedback classes."""

    def test_quiz_feedback_has_thematic_and_tutor(self):
        """QuizFeedback should include thematic insights and tutor's note."""
        from edps.evaluation import QuizFeedback, AnswerFeedback, ThematicInsights, WritingScores

        writing = WritingScores(precision=4, clarity=4, economy=3, suggestion="Lead with mechanism.")
        insights = ThematicInsights(
            source_mastery="Strong on core thesis.",
            reasoning_quality="Sound logic.",
            writing_craft=writing,
        )
        feedback = QuizFeedback(
            answers=[AnswerFeedback(label="Q1", correct=True, note="Good", score=1.0)],
            total_score=7.5,
            reasoning="Legacy reasoning",
            thematic_insights=insights,
            tutors_note="You're building real understanding. Three things to carry forward...",
        )
        assert feedback.thematic_insights.writing_craft.precision == 4
        assert "Three things" in feedback.tutors_note


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
            assert "**Score:** 5/5" in recall_content
            assert "## AI Feedback" in quiz_content
            assert "**Total Score:** 8/8" in quiz_content


class TestExpandedEvaluationPrompt:
    """Tests for expanded evaluation prompt."""

    def test_prompt_requests_per_answer_analysis(self):
        """Prompt should request accuracy/reasoning/writing for each answer."""
        from edps.evaluation import build_evaluation_prompt

        source = "Division of labor increases productivity."
        recall = "## From Memory\n\n1. Specialization helps.\n\n## One Sentence\n\nLabor division is key."
        quiz = "### 1. Main\n\nWhat helps?\n\n**Answer:** Specialization"

        prompt = build_evaluation_prompt(source, recall, quiz)
        assert "accuracy" in prompt.lower()
        assert "reasoning" in prompt.lower()
        assert "writing" in prompt.lower()

    def test_prompt_requests_thematic_insights(self):
        """Prompt should request thematic insights section."""
        from edps.evaluation import build_evaluation_prompt

        source = "Test"
        recall = "## From Memory\n\n1. Test\n\n## One Sentence\n\nTest"
        quiz = "### 1. T\n\nT?\n\n**Answer:** T"

        prompt = build_evaluation_prompt(source, recall, quiz)
        assert "source_mastery" in prompt or "thematic" in prompt.lower()
        assert "precision" in prompt.lower()
        assert "clarity" in prompt.lower()
        assert "economy" in prompt.lower()

    def test_prompt_requests_tutors_note(self):
        """Prompt should request narrative tutor's note."""
        from edps.evaluation import build_evaluation_prompt

        source = "Test"
        recall = "## From Memory\n\n1. Test\n\n## One Sentence\n\nTest"
        quiz = "### 1. T\n\nT?\n\n**Answer:** T"

        prompt = build_evaluation_prompt(source, recall, quiz)
        assert "tutor" in prompt.lower() or "narrative" in prompt.lower()


class TestExpandedResponseParsing:
    """Tests for parsing expanded evaluation responses."""

    def test_parses_per_answer_details(self):
        """Should parse accuracy/reasoning/writing from response."""
        from edps.evaluation import parse_evaluation_response

        response = '''{
  "recall": {
    "points": [
      {"label": "Main claim", "correct": true, "note": "Good", "accuracy": "Correct on origin.", "reasoning": "Sound logic.", "writing": "Use 'propensity' not 'innate'."}
    ],
    "one_sentence_ok": true,
    "one_sentence_note": "Clear",
    "score": 4,
    "reasoning": "Strong"
  },
  "quiz": {
    "answers": [
      {"label": "Q1", "correct": true, "score": 1.0, "note": "OK", "accuracy": "Right.", "reasoning": "Good.", "writing": "Concise."}
    ],
    "total_score": 7.5,
    "reasoning": "Good",
    "thematic_insights": {
      "source_mastery": "You grasp the core.",
      "reasoning_quality": "Sound arguments.",
      "writing_craft": {"precision": 4, "clarity": 4, "economy": 3, "suggestion": "Cut filler."}
    },
    "tutors_note": "You're building understanding. Carry forward: honor the hedges."
  }
}'''

        recall_fb, quiz_fb = parse_evaluation_response(response)

        assert recall_fb.points[0].accuracy == "Correct on origin."
        assert recall_fb.points[0].reasoning == "Sound logic."
        assert recall_fb.points[0].writing == "Use 'propensity' not 'innate'."

        assert quiz_fb.thematic_insights.writing_craft.precision == 4
        assert quiz_fb.tutors_note == "You're building understanding. Carry forward: honor the hedges."


class TestExpandedMarkdownFormat:
    """Tests for expanded markdown output."""

    def test_quiz_feedback_includes_per_answer_sections(self):
        """Should format each answer with Accuracy/Reasoning/Writing."""
        from edps.evaluation import (
            format_quiz_feedback, QuizFeedback, AnswerFeedback,
            ThematicInsights, WritingScores
        )

        writing = WritingScores(precision=4, clarity=4, economy=3, suggestion="Cut filler.")
        insights = ThematicInsights(
            source_mastery="Strong on core thesis.",
            reasoning_quality="Sound logic throughout.",
            writing_craft=writing,
        )
        feedback = QuizFeedback(
            answers=[
                AnswerFeedback(
                    label="Q1: Main Claim", correct=True, note="Good", score=1.0,
                    accuracy="Correct on origin.", reasoning="Sound chain.", writing="Use 'propensity'."
                ),
            ],
            total_score=7.5,
            reasoning="Good overall",
            thematic_insights=insights,
            tutors_note="You're building understanding. Honor the hedges.",
        )

        markdown = format_quiz_feedback(feedback, "2025-12-27", "source.txt")

        # Per-answer sections
        assert "#### Q1: Main Claim" in markdown
        assert "**Accuracy:**" in markdown
        assert "**Reasoning:**" in markdown
        assert "**Writing:**" in markdown

        # Thematic insights
        assert "### Thematic Insights" in markdown
        assert "#### Source Mastery" in markdown
        assert "Strong on core thesis" in markdown
        assert "**Precision:** 4/5" in markdown

        # Tutor's note
        assert "### Tutor's Note" in markdown
        assert "Honor the hedges" in markdown


class TestExpandedRecallFormat:
    """Tests for expanded recall feedback markdown output."""

    def test_recall_feedback_includes_per_point_sections(self):
        """Should format each recall point with Accuracy/Reasoning/Writing."""
        from edps.evaluation import format_recall_feedback, RecallFeedback, AnswerFeedback

        feedback = RecallFeedback(
            points=[
                AnswerFeedback(
                    label="Division of labor",
                    correct=True,
                    note="Good understanding",
                    accuracy="Correctly identified the main mechanism.",
                    reasoning="Causal chain is complete.",
                    writing="Consider using Smith's exact terminology."
                ),
            ],
            one_sentence_ok=True,
            one_sentence_note="Clear and accurate",
            score=4,
            reasoning="Strong recall of key concepts"
        )

        markdown = format_recall_feedback(feedback, "2025-12-27", "source.txt")

        # Per-point sections
        assert "#### Division of labor" in markdown
        assert "**Accuracy:**" in markdown
        assert "Correctly identified the main mechanism" in markdown
        assert "**Reasoning:**" in markdown
        assert "**Writing:**" in markdown

        # Score and summary
        assert "**Score:** 4/5" in markdown


class TestExpandedEvaluationIntegration:
    """Integration test for full expanded evaluation."""

    def test_full_expanded_evaluation_flow(self, tmp_path):
        """Test complete flow produces expanded feedback structure."""
        from edps.evaluation import (
            build_evaluation_prompt, parse_evaluation_response,
            format_quiz_feedback, format_recall_feedback,
            QuizFeedback, RecallFeedback, AnswerFeedback,
            ThematicInsights, WritingScores
        )

        # Create mock expanded response (what the LLM would return)
        mock_response = '''{
  "recall": {
    "points": [
      {
        "label": "Division of labor origin",
        "correct": true,
        "note": "Good understanding of propensity to exchange",
        "accuracy": "Correctly identified propensity to exchange as the origin.",
        "reasoning": "Causal chain is complete - exchange enables specialization.",
        "writing": "Consider using 'propensity' over 'innate tendency'."
      },
      {
        "label": "Productivity gains",
        "correct": true,
        "note": "Solid grasp of three causes",
        "accuracy": "All three causes mentioned: dexterity, time saving, machinery.",
        "reasoning": "Good logical flow from cause to effect.",
        "writing": "Lead with the mechanism before the examples."
      }
    ],
    "one_sentence_ok": true,
    "one_sentence_note": "Clear and accurate summary that captures the core thesis.",
    "score": 4,
    "reasoning": "Strong recall of key concepts with good accuracy."
  },
  "quiz": {
    "answers": [
      {
        "label": "Q1: Origin of Division of Labor",
        "correct": true,
        "score": 1.0,
        "note": "Excellent",
        "accuracy": "Correctly identified propensity to exchange.",
        "reasoning": "Sound causal logic.",
        "writing": "Concise and precise."
      },
      {
        "label": "Q2: Three Causes of Productivity",
        "correct": true,
        "score": 0.8,
        "note": "Mostly correct",
        "accuracy": "Two of three causes identified correctly.",
        "reasoning": "Good but missing machinery innovation aspect.",
        "writing": "Structure could be clearer."
      }
    ],
    "total_score": 6.8,
    "reasoning": "Strong understanding with minor gaps.",
    "thematic_insights": {
      "source_mastery": "You grasp Smith's core thesis well. Pattern: you tend to sharpen his hedges into certainties.",
      "reasoning_quality": "Arguments are structurally sound. Push the 'so what' further in applications.",
      "writing_craft": {
        "precision": 4,
        "clarity": 4,
        "economy": 3,
        "suggestion": "Cut 20% of words without losing meaning - practice the 'one-sentence version' first."
      }
    },
    "tutors_note": "You're building real understanding here. Three things to carry forward: (1) Honor Smith's hedges - he says 'propensity' not 'innate need' for a reason. (2) When listing causes, lead with the mechanism before examples. (3) Your synthesis is getting stronger - keep connecting back to the core thesis."
  }
}'''

        # Parse the response
        recall_fb, quiz_fb = parse_evaluation_response(mock_response)

        # Verify recall feedback has expanded fields
        assert len(recall_fb.points) == 2
        assert recall_fb.points[0].accuracy is not None
        assert recall_fb.points[0].reasoning is not None
        assert recall_fb.points[0].writing is not None
        assert recall_fb.score == 4

        # Verify quiz feedback has thematic insights
        assert quiz_fb.thematic_insights is not None
        assert quiz_fb.thematic_insights.source_mastery is not None
        assert quiz_fb.thematic_insights.writing_craft.precision == 4
        assert quiz_fb.thematic_insights.writing_craft.suggestion is not None

        # Verify tutor's note
        assert quiz_fb.tutors_note is not None
        assert "Honor Smith's hedges" in quiz_fb.tutors_note

        # Format and verify output structure
        quiz_md = format_quiz_feedback(quiz_fb, "2025-12-27", "wealth-of-nations/001")
        recall_md = format_recall_feedback(recall_fb, "2025-12-27", "wealth-of-nations/001")

        # Verify quiz markdown has expected sections
        assert "### Per-Answer Analysis" in quiz_md
        assert "**Accuracy:**" in quiz_md
        assert "### Thematic Insights" in quiz_md
        assert "#### Source Mastery" in quiz_md
        assert "**Precision:** 4/5" in quiz_md
        assert "### Tutor's Note" in quiz_md

        # Verify recall markdown has expected sections
        assert "### Recall Points" in recall_md
        assert "**Accuracy:**" in recall_md
        assert "### One Sentence Summary" in recall_md

        # Verify approximate output length (~800-1000 words for quiz)
        quiz_word_count = len(quiz_md.split())
        assert quiz_word_count > 100  # Should be substantial


class TestInlineErrorDataclass:
    """Tests for InlineError dataclass."""

    def test_inline_error_creation(self):
        """InlineError should hold quoted text and feedback."""
        from edps.evaluation import InlineError

        error = InlineError(
            quoted_text="Specialization leads to division of labor",
            summary="Causal inversion",
            feedback="Exchange certainty enables specialization, not the reverse."
        )
        assert error.quoted_text == "Specialization leads to division of labor"
        assert error.summary == "Causal inversion"
        assert error.feedback == "Exchange certainty enables specialization, not the reverse."


class TestInlineAnswerFeedback:
    """Tests for InlineAnswerFeedback dataclass."""

    def test_inline_answer_feedback_creation(self):
        """InlineAnswerFeedback should hold errors and writing note."""
        from edps.evaluation import InlineAnswerFeedback, InlineError

        feedback = InlineAnswerFeedback(
            question_id="q1",
            label="Q1: Main Claim",
            score=0.5,
            errors=[
                InlineError(
                    quoted_text="Specialization leads to division",
                    summary="Causal inversion",
                    feedback="Exchange enables specialization."
                )
            ],
            writing_note="Lead with causes before effects. Example: 'Exchange certainty motivates specialization.'"
        )
        assert feedback.question_id == "q1"
        assert len(feedback.errors) == 1
        assert feedback.writing_note is not None

    def test_inline_answer_feedback_optional_fields(self):
        """InlineAnswerFeedback should allow empty errors and null writing_note."""
        from edps.evaluation import InlineAnswerFeedback

        feedback = InlineAnswerFeedback(
            question_id="q2",
            label="Q2: Mechanism",
            score=1.0,
            errors=[],
            writing_note=None
        )
        assert len(feedback.errors) == 0
        assert feedback.writing_note is None


class TestSchemaMigration:
    """Tests for v0 -> v1 schema migration."""

    def test_migrate_v0_to_v1_maps_note_to_explanation(self):
        """Migration should map legacy 'note' field to 'explanation'."""
        from edps.evaluation import migrate_v0_to_v1

        v0_data = {
            "quiz": {
                "answers": [
                    {"label": "Q1", "correct": True, "note": "Good answer", "score": 1.0}
                ],
                "total_score": 7.5,
                "reasoning": "Overall good"
            }
        }

        v1_data = migrate_v0_to_v1(v0_data)

        assert v1_data["quiz"]["schema_version"] == "v1"
        assert v1_data["quiz"]["answers"][0]["explanation"] == "Good answer"
        assert v1_data["quiz"]["answers"][0]["question_id"] == "q1"

    def test_migrate_v0_to_v1_preserves_existing_v1(self):
        """Migration should pass through v1 data unchanged."""
        from edps.evaluation import migrate_v0_to_v1

        v1_data = {
            "quiz": {
                "schema_version": "v1",
                "answers": [{"question_id": "q1", "explanation": "Good"}],
                "total_score": 7.5,
                "reasoning": "Overall good"
            }
        }

        result = migrate_v0_to_v1(v1_data)
        assert result == v1_data  # Unchanged


class TestInjectError:
    """Tests for inject_error function."""

    def test_injects_after_quoted_text(self):
        """Should insert <details> block after exact quoted text."""
        from edps.evaluation import inject_error, InlineError

        content = "Division of labor results from exchange. Specialization leads to surplus."
        error = InlineError(
            quoted_text="Specialization leads to surplus",
            summary="Causal inversion",
            feedback="Exchange enables specialization, not vice versa."
        )

        result = inject_error(content, error)

        assert "Specialization leads to surplus" in result
        assert "<details>" in result
        assert "<summary>Causal inversion</summary>" in result
        assert "Exchange enables specialization" in result
        # Verify order: quoted text comes before details block
        assert result.index("Specialization leads to surplus") < result.index("<details>")

    def test_handles_text_not_found(self):
        """Should return content unchanged if quoted text not found."""
        from edps.evaluation import inject_error, InlineError

        content = "Some answer text here."
        error = InlineError(
            quoted_text="nonexistent text",
            summary="Error",
            feedback="Feedback"
        )

        result = inject_error(content, error)
        assert result == content  # Unchanged

    def test_only_injects_first_occurrence(self):
        """Should only annotate first occurrence of repeated text."""
        from edps.evaluation import inject_error, InlineError

        content = "Exchange is key. Exchange is key again."
        error = InlineError(
            quoted_text="Exchange is key",
            summary="Clarification",
            feedback="Be more specific."
        )

        result = inject_error(content, error)
        assert result.count("<details>") == 1


class TestInjectWritingNote:
    """Tests for inject_writing_note function."""

    def test_injects_at_end_of_answer(self):
        """Should append writing note at end of answer text."""
        from edps.evaluation import inject_writing_note

        answer = "Division of labor results from exchange. This leads to surplus."
        writing_note = 'Lead with causes. Example: "Exchange certainty motivates specialization."'

        result = inject_writing_note(answer, writing_note)

        assert "<details>" in result
        assert "<summary>Writing</summary>" in result
        assert "Lead with causes" in result
        assert "Exchange certainty" in result

    def test_returns_unchanged_if_no_note(self):
        """Should return answer unchanged if writing_note is None."""
        from edps.evaluation import inject_writing_note

        answer = "Some answer text."
        result = inject_writing_note(answer, None)
        assert result == answer

    def test_returns_unchanged_if_empty_note(self):
        """Should return answer unchanged if writing_note is empty."""
        from edps.evaluation import inject_writing_note

        answer = "Some answer text."
        result = inject_writing_note(answer, "")
        assert result == answer


class TestStripFeedback:
    """Tests for strip_feedback function."""

    def test_removes_details_blocks(self):
        """Should remove all <details> blocks from content."""
        from edps.evaluation import strip_feedback

        content = '''**Answer:** First sentence.
Second sentence.
<details>
<summary>Error</summary>
Feedback here.
</details>
Third sentence.
'''
        result = strip_feedback(content)
        assert "<details>" not in result
        assert "</details>" not in result
        assert "First sentence" in result
        assert "Third sentence" in result

    def test_removes_multiple_details_blocks(self):
        """Should remove multiple <details> blocks."""
        from edps.evaluation import strip_feedback

        content = '''Answer text.
<details>
<summary>Error 1</summary>
Feedback 1.
</details>
More text.
<details>
<summary>Error 2</summary>
Feedback 2.
</details>
Final text.
'''
        result = strip_feedback(content)
        assert result.count("<details>") == 0
        assert "Answer text" in result
        assert "More text" in result
        assert "Final text" in result

    def test_preserves_content_without_details(self):
        """Should return content unchanged if no <details> blocks."""
        from edps.evaluation import strip_feedback

        content = "Plain markdown without feedback."
        result = strip_feedback(content)
        assert result == content

    def test_removes_summary_section(self):
        """Should remove ## Summary section at end of file."""
        from edps.evaluation import strip_feedback

        content = '''### 1. Question

**Answer:** My answer.

---

## Summary

**Score:** 6/8

<details>
<summary>Thematic Insights</summary>
Content here.
</details>
'''
        result = strip_feedback(content)
        assert "## Summary" not in result
        assert "**Score:** 6/8" not in result


class TestInjectInlineFeedback:
    """Tests for inject_inline_feedback function."""

    def test_injects_errors_into_answer(self):
        """Should inject all errors and writing note into quiz content."""
        from edps.evaluation import inject_inline_feedback, InlineAnswerFeedback, InlineError

        content = '''### 1. Main Claim

What is the origin?

**Answer:** Division of labor results from exchange. Specialization leads to surplus.

---
'''
        feedbacks = [
            InlineAnswerFeedback(
                question_id="q1",
                label="Q1: Main Claim",
                score=0.5,
                errors=[
                    InlineError(
                        quoted_text="Specialization leads to surplus",
                        summary="Causal inversion",
                        feedback="Exchange enables specialization."
                    )
                ],
                writing_note="Lead with causes before effects."
            )
        ]

        result = inject_inline_feedback(content, feedbacks)

        # Error should be injected after quoted text
        assert "<summary>Causal inversion</summary>" in result
        assert "Exchange enables specialization" in result

        # Writing note should be at end of answer
        assert "<summary>Writing</summary>" in result
        assert "Lead with causes" in result

    def test_handles_no_errors(self):
        """Should leave answer unchanged if no errors and no writing note."""
        from edps.evaluation import inject_inline_feedback, InlineAnswerFeedback

        content = '''### 1. Q1

**Answer:** Perfect answer.

---
'''
        feedbacks = [
            InlineAnswerFeedback(
                question_id="q1",
                label="Q1",
                score=1.0,
                errors=[],
                writing_note=None
            )
        ]

        result = inject_inline_feedback(content, feedbacks)
        assert "<details>" not in result


class TestFormatSummaryFeedback:
    """Tests for format_summary_feedback function."""

    def test_generates_collapsible_summary(self):
        """Should generate slimmed-down summary with collapsible sections."""
        from edps.evaluation import format_summary_feedback, QuizFeedback, ThematicInsights, WritingScores

        writing = WritingScores(precision=4, clarity=4, economy=3, suggestion="Cut filler.")
        insights = ThematicInsights(
            source_mastery="Strong grasp of core thesis.",
            reasoning_quality="Sound logic throughout.",
            writing_craft=writing,
        )
        feedback = QuizFeedback(
            answers=[],
            total_score=6,
            reasoning="",
            thematic_insights=insights,
            tutors_note="You're building understanding. Keep it up.",
        )

        result = format_summary_feedback(feedback, "2025-12-28")

        assert "## Summary" in result
        assert "**Score:** 6/8" in result
        assert "2025-12-28" in result
        assert "<details>" in result
        assert "<summary>Thematic Insights</summary>" in result
        assert "Strong grasp" in result
        assert "<summary>Tutor's Note</summary>" in result
        assert "building understanding" in result

    def test_omits_sections_if_missing(self):
        """Should omit thematic insights or tutor's note if not present."""
        from edps.evaluation import format_summary_feedback, QuizFeedback

        feedback = QuizFeedback(
            answers=[],
            total_score=7,
            reasoning="",
            thematic_insights=None,
            tutors_note=None,
        )

        result = format_summary_feedback(feedback, "2025-12-28")

        assert "## Summary" in result
        assert "**Score:** 7/8" in result
        assert "Thematic Insights" not in result
        assert "Tutor's Note" not in result


class TestInlinePromptSchema:
    """Tests for inline feedback prompt schema."""

    def test_prompt_requests_errors_array(self):
        """Prompt should request errors[] with quoted_text."""
        from edps.evaluation import build_evaluation_prompt

        source = "Test source"
        recall = "## From Memory\n\n1. Test\n\n## One Sentence\n\nTest"
        quiz = "### 1. Q1\n\nQ?\n\n**Answer:** Test answer here."

        prompt = build_evaluation_prompt(source, recall, quiz)

        assert "errors" in prompt
        assert "quoted_text" in prompt

    def test_prompt_requests_writing_note(self):
        """Prompt should request writing_note with rewrite example."""
        from edps.evaluation import build_evaluation_prompt

        source = "Test"
        recall = "## From Memory\n\n1. Test\n\n## One Sentence\n\nTest"
        quiz = "### 1. Q1\n\nQ?\n\n**Answer:** T"

        prompt = build_evaluation_prompt(source, recall, quiz)

        assert "writing_note" in prompt
