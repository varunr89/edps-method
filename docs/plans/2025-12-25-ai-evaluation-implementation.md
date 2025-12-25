# AI Evaluation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add AI-powered evaluation of recall and quiz answers, triggered via pre-commit hook or manual command.

**Architecture:** New `evaluation.py` module handles prompt construction and response parsing. Uses existing `LLMClient` for API calls. Extends pre-commit hook to call evaluation. Feedback appended to markdown files.

**Tech Stack:** Python 3.11+, Typer CLI, AnthropicFoundry (existing), ruamel.yaml, pytest

---

## Task 1: Create Evaluation Dataclasses

**Files:**
- Create: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
# tests/test_evaluation.py
"""Tests for AI evaluation module."""
from edps.evaluation import RecallFeedback, QuizFeedback, AnswerFeedback


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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestDataclasses -v`
Expected: FAIL with "No module named 'edps.evaluation'"

**Step 3: Write minimal implementation**

```python
# tools/edps/evaluation.py
"""AI-powered evaluation of recall and quiz answers."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnswerFeedback:
    """Feedback for a single answer or recall point."""
    label: str
    correct: bool
    note: str
    score: Optional[float] = None  # For quiz questions


@dataclass
class RecallFeedback:
    """Complete feedback for recall.md evaluation."""
    points: list[AnswerFeedback]
    one_sentence_ok: bool
    one_sentence_note: str
    score: int  # 0-5
    reasoning: str


@dataclass
class QuizFeedback:
    """Complete feedback for quiz.md evaluation."""
    answers: list[AnswerFeedback]
    total_score: float  # 0-8
    reasoning: str
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestDataclasses -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add evaluation dataclasses"
```

---

## Task 2: Parse Recall Content

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_evaluation.py
from edps.evaluation import parse_recall_content


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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestParseRecallContent -v`
Expected: FAIL with "cannot import name 'parse_recall_content'"

**Step 3: Write minimal implementation**

```python
# Add to tools/edps/evaluation.py
import re


def parse_recall_content(content: str) -> dict:
    """Parse recall.md content into structured data.

    Args:
        content: Raw markdown content of recall.md

    Returns:
        Dict with memory_points (list[str]) and one_sentence (str)
    """
    result = {"memory_points": [], "one_sentence": ""}

    # Extract numbered points from "From Memory" section
    memory_match = re.search(
        r"## From Memory.*?\n\n.*?\n\n((?:\d+\..*?\n)+)",
        content,
        re.DOTALL
    )
    if memory_match:
        points_text = memory_match.group(1)
        points = re.findall(r"\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\Z)", points_text, re.DOTALL)
        result["memory_points"] = [p.strip() for p in points]

    # Extract one sentence summary
    sentence_match = re.search(
        r"## One Sentence.*?\n\n(.+?)(?=\n---|\n##|\Z)",
        content,
        re.DOTALL
    )
    if sentence_match:
        result["one_sentence"] = sentence_match.group(1).strip()

    return result
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestParseRecallContent -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add recall content parser"
```

---

## Task 3: Parse Quiz Content

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_evaluation.py
from edps.evaluation import parse_quiz_content


class TestParseQuizContent:
    """Tests for parsing quiz.md content."""

    def test_extracts_questions_and_answers(self):
        """Should extract question-answer pairs."""
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestParseQuizContent -v`
Expected: FAIL with "cannot import name 'parse_quiz_content'"

**Step 3: Write minimal implementation**

```python
# Add to tools/edps/evaluation.py

def parse_quiz_content(content: str) -> dict:
    """Parse quiz.md content into structured data.

    Args:
        content: Raw markdown content of quiz.md

    Returns:
        Dict with qa_pairs (list of {number, title, question, answer})
    """
    result = {"qa_pairs": []}

    # Pattern: ### N. Title\n\nQuestion\n\n**Answer:** Answer text
    pattern = r"### (\d+)\. (.+?)\n\n(.+?)\n\n\*\*Answer:\*\*\s*(.+?)(?=\n---|\n###|\Z)"

    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        result["qa_pairs"].append({
            "number": match[0],
            "title": match[1].strip(),
            "question": match[2].strip(),
            "answer": match[3].strip(),
        })

    return result
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestParseQuizContent -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add quiz content parser"
```

---

## Task 4: Build Evaluation Prompt

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_evaluation.py
from edps.evaluation import build_evaluation_prompt


class TestBuildEvaluationPrompt:
    """Tests for evaluation prompt construction."""

    def test_includes_source_text(self):
        """Prompt should include source text."""
        prompt = build_evaluation_prompt(
            source_text="Smith argues that division of labor...",
            recall_content={"memory_points": ["Point 1"], "one_sentence": "Summary"},
            quiz_content={"qa_pairs": []},
        )
        assert "Smith argues" in prompt

    def test_includes_user_answers(self):
        """Prompt should include user's recall and quiz answers."""
        prompt = build_evaluation_prompt(
            source_text="Source",
            recall_content={"memory_points": ["My point"], "one_sentence": "My summary"},
            quiz_content={"qa_pairs": [{"number": "1", "title": "Q1", "question": "What?", "answer": "This"}]},
        )
        assert "My point" in prompt
        assert "My summary" in prompt
        assert "This" in prompt

    def test_requests_json_output(self):
        """Prompt should request structured JSON output."""
        prompt = build_evaluation_prompt(
            source_text="Source",
            recall_content={"memory_points": [], "one_sentence": ""},
            quiz_content={"qa_pairs": []},
        )
        assert "JSON" in prompt
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestBuildEvaluationPrompt -v`
Expected: FAIL with "cannot import name 'build_evaluation_prompt'"

**Step 3: Write minimal implementation**

```python
# Add to tools/edps/evaluation.py

def build_evaluation_prompt(
    source_text: str,
    recall_content: dict,
    quiz_content: dict,
) -> str:
    """Build the evaluation prompt for Claude.

    Args:
        source_text: Original source text for the section
        recall_content: Parsed recall.md content
        quiz_content: Parsed quiz.md content

    Returns:
        Complete prompt string for evaluation
    """
    memory_points = "\n".join(
        f"{i+1}. {p}" for i, p in enumerate(recall_content["memory_points"])
    )

    quiz_section = ""
    for qa in quiz_content["qa_pairs"]:
        quiz_section += f"""
Q{qa['number']}. {qa['title']}
Question: {qa['question']}
User's Answer: {qa['answer']}
"""

    return f'''You are evaluating a student's understanding of a text. Be generous - credit directionally correct answers.

## SOURCE TEXT
{source_text}

## STUDENT'S RECALL (from memory)
{memory_points}

One-sentence summary: {recall_content["one_sentence"]}

## STUDENT'S QUIZ ANSWERS
{quiz_section}

## YOUR TASK
Evaluate the student's answers against the source text. Return your evaluation as JSON:

```json
{{
  "recall": {{
    "points": [
      {{"label": "Point 1 topic", "correct": true, "note": "Brief note"}},
      ...
    ],
    "one_sentence_ok": true,
    "one_sentence_note": "Assessment of summary",
    "score": 4,
    "reasoning": "Overall assessment"
  }},
  "quiz": {{
    "answers": [
      {{"label": "Q1", "correct": true, "score": 1.0, "note": "Brief note"}},
      ...
    ],
    "total_score": 7.5,
    "reasoning": "Overall assessment"
  }}
}}
```

RULES:
- Recall score: 0-5 (5 = excellent recall)
- Quiz: Each question worth 1 point, partial credit 0.5 allowed
- Be generous: credit directionally correct answers
- For correct answers: note = "Correct" (keep brief)
- For incorrect/partial: explain what was missed with source reference
'''
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestBuildEvaluationPrompt -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add evaluation prompt builder"
```

---

## Task 5: Parse LLM Response

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_evaluation.py
import json
from edps.evaluation import parse_evaluation_response


class TestParseEvaluationResponse:
    """Tests for parsing LLM evaluation response."""

    def test_parses_valid_json(self):
        """Should parse valid JSON response into feedback objects."""
        response = json.dumps({
            "recall": {
                "points": [{"label": "P1", "correct": True, "note": "Good"}],
                "one_sentence_ok": True,
                "one_sentence_note": "Strong",
                "score": 4,
                "reasoning": "Good overall"
            },
            "quiz": {
                "answers": [{"label": "Q1", "correct": True, "score": 1.0, "note": "Correct"}],
                "total_score": 7.5,
                "reasoning": "Strong"
            }
        })
        recall, quiz = parse_evaluation_response(response)
        assert recall.score == 4
        assert quiz.total_score == 7.5

    def test_handles_json_in_markdown(self):
        """Should extract JSON from markdown code blocks."""
        response = '''Here's my evaluation:

```json
{"recall": {"points": [], "one_sentence_ok": true, "one_sentence_note": "", "score": 3, "reasoning": ""}, "quiz": {"answers": [], "total_score": 6, "reasoning": ""}}
```
'''
        recall, quiz = parse_evaluation_response(response)
        assert recall.score == 3
        assert quiz.total_score == 6
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestParseEvaluationResponse -v`
Expected: FAIL with "cannot import name 'parse_evaluation_response'"

**Step 3: Write minimal implementation**

```python
# Add to tools/edps/evaluation.py
import json


def parse_evaluation_response(response: str) -> tuple[RecallFeedback, QuizFeedback]:
    """Parse LLM response into feedback objects.

    Args:
        response: Raw LLM response (may contain JSON in markdown)

    Returns:
        Tuple of (RecallFeedback, QuizFeedback)
    """
    # Extract JSON from markdown code block if present
    json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response

    data = json.loads(json_str)

    # Build RecallFeedback
    recall_data = data["recall"]
    recall = RecallFeedback(
        points=[
            AnswerFeedback(
                label=p["label"],
                correct=p["correct"],
                note=p["note"],
            )
            for p in recall_data["points"]
        ],
        one_sentence_ok=recall_data["one_sentence_ok"],
        one_sentence_note=recall_data["one_sentence_note"],
        score=recall_data["score"],
        reasoning=recall_data["reasoning"],
    )

    # Build QuizFeedback
    quiz_data = data["quiz"]
    quiz = QuizFeedback(
        answers=[
            AnswerFeedback(
                label=a["label"],
                correct=a["correct"],
                note=a["note"],
                score=a.get("score", 1.0 if a["correct"] else 0.0),
            )
            for a in quiz_data["answers"]
        ],
        total_score=quiz_data["total_score"],
        reasoning=quiz_data["reasoning"],
    )

    return recall, quiz
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestParseEvaluationResponse -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add LLM response parser"
```

---

## Task 6: Format Feedback as Markdown

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_evaluation.py
from edps.evaluation import format_recall_feedback, format_quiz_feedback


class TestFormatFeedback:
    """Tests for formatting feedback as markdown."""

    def test_recall_feedback_format(self):
        """Should format recall feedback as markdown table."""
        feedback = RecallFeedback(
            points=[
                AnswerFeedback(label="Main claim", correct=True, note="Correct"),
                AnswerFeedback(label="Mechanism", correct=False, note="Missed X"),
            ],
            one_sentence_ok=True,
            one_sentence_note="Strong summary",
            score=4,
            reasoning="Good overall",
        )
        md = format_recall_feedback(feedback, "2025-12-25", "source.txt")
        assert "## AI Feedback" in md
        assert "| Main claim | ✓ |" in md
        assert "| Mechanism | ⚠️ |" in md
        assert "### AI Score: 4 / 5" in md

    def test_quiz_feedback_format(self):
        """Should format quiz feedback as markdown table."""
        feedback = QuizFeedback(
            answers=[
                AnswerFeedback(label="Q1", correct=True, score=1.0, note="Correct"),
                AnswerFeedback(label="Q2", correct=False, score=0.5, note="Partial"),
            ],
            total_score=7.5,
            reasoning="Strong comprehension",
        )
        md = format_quiz_feedback(feedback, "2025-12-25", "source.txt")
        assert "## AI Feedback" in md
        assert "| Q1 | ✓ 1/1 |" in md
        assert "| Q2 | ⚠️ 0.5/1 |" in md
        assert "### AI Score: 7.5 / 8" in md
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestFormatFeedback -v`
Expected: FAIL with "cannot import name 'format_recall_feedback'"

**Step 3: Write minimal implementation**

```python
# Add to tools/edps/evaluation.py
from datetime import date


def format_recall_feedback(feedback: RecallFeedback, eval_date: str, source_file: str) -> str:
    """Format recall feedback as markdown to append to recall.md.

    Args:
        feedback: RecallFeedback object
        eval_date: Evaluation date string
        source_file: Name of source file used

    Returns:
        Markdown string to append
    """
    lines = [
        "",
        "---",
        "",
        "## AI Feedback",
        "",
        f"> Evaluated: {eval_date}",
        f"> Source: {source_file}",
        "",
        "### From Memory Assessment",
        "",
        "| Point | Score | Note |",
        "|-------|-------|------|",
    ]

    for p in feedback.points:
        icon = "✓" if p.correct else "⚠️"
        lines.append(f"| {p.label} | {icon} | {p.note} |")

    # Add details for incorrect points
    incorrect = [p for p in feedback.points if not p.correct]
    if incorrect:
        lines.append("")
        for p in incorrect:
            lines.append(f"**{p.label} detail:** {p.note}")

    lines.extend([
        "",
        "### One Sentence Assessment",
        "",
        f"{'✓' if feedback.one_sentence_ok else '⚠️'} {feedback.one_sentence_note}",
        "",
        f"### AI Score: {feedback.score} / 5",
        "",
        f"**Reasoning:** {feedback.reasoning}",
    ])

    return "\n".join(lines)


def format_quiz_feedback(feedback: QuizFeedback, eval_date: str, source_file: str) -> str:
    """Format quiz feedback as markdown to append to quiz.md.

    Args:
        feedback: QuizFeedback object
        eval_date: Evaluation date string
        source_file: Name of source file used

    Returns:
        Markdown string to append
    """
    lines = [
        "",
        "---",
        "",
        "## AI Feedback",
        "",
        f"> Evaluated: {eval_date}",
        f"> Source: {source_file}",
        "",
        "### Question Scores",
        "",
        "| Q | Score | Feedback |",
        "|---|-------|----------|",
    ]

    for a in feedback.answers:
        icon = "✓" if a.correct else "⚠️"
        score_str = f"{a.score}/1" if a.score is not None else "—"
        lines.append(f"| {a.label} | {icon} {score_str} | {a.note} |")

    # Add details for incorrect answers
    incorrect = [a for a in feedback.answers if not a.correct]
    if incorrect:
        lines.append("")
        for a in incorrect:
            lines.append(f"**{a.label} detail:** {a.note}")

    lines.extend([
        "",
        f"### AI Score: {feedback.total_score} / 8",
        "",
        f"**Reasoning:** {feedback.reasoning}",
    ])

    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestFormatFeedback -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add markdown feedback formatters"
```

---

## Task 7: Main Evaluate Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_evaluation.py
from pathlib import Path
from unittest.mock import MagicMock, patch
from edps.evaluation import evaluate_section


class TestEvaluateSection:
    """Tests for main evaluate_section function."""

    def test_reads_required_files(self, tmp_path):
        """Should read source, recall, and quiz files."""
        # Setup section directory
        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)

        (section / "EDPS-test-001.txt").write_text("Source content")
        (section / "recall.md").write_text("## From Memory\n\n1. Point one\n\n## One Sentence\n\nSummary")
        (section / "quiz.md").write_text("### 1. Q1\n\nQuestion?\n\n**Answer:** Answer here")

        with patch("edps.evaluation.LLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.complete.return_value.content = '{"recall": {"points": [], "one_sentence_ok": true, "one_sentence_note": "", "score": 4, "reasoning": ""}, "quiz": {"answers": [], "total_score": 7, "reasoning": ""}}'
            mock_client.return_value = mock_instance

            result = evaluate_section(section, "test", "001")

            assert result is not None
            assert mock_instance.complete.called

    def test_appends_feedback_to_files(self, tmp_path):
        """Should append AI feedback to recall.md and quiz.md."""
        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)

        (section / "EDPS-test-001.txt").write_text("Source")
        (section / "recall.md").write_text("# Recall\n\n## From Memory\n\n1. Point\n\n## One Sentence\n\nSum")
        (section / "quiz.md").write_text("### 1. Q1\n\nQ?\n\n**Answer:** A")

        with patch("edps.evaluation.LLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.complete.return_value.content = '{"recall": {"points": [{"label": "P1", "correct": true, "note": "OK"}], "one_sentence_ok": true, "one_sentence_note": "Good", "score": 4, "reasoning": "Good"}, "quiz": {"answers": [{"label": "Q1", "correct": true, "score": 1.0, "note": "OK"}], "total_score": 7, "reasoning": "Good"}}'
            mock_client.return_value = mock_instance

            evaluate_section(section, "test", "001")

            recall_content = (section / "recall.md").read_text()
            quiz_content = (section / "quiz.md").read_text()

            assert "## AI Feedback" in recall_content
            assert "## AI Feedback" in quiz_content
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestEvaluateSection -v`
Expected: FAIL with "cannot import name 'evaluate_section'"

**Step 3: Write minimal implementation**

```python
# Add to tools/edps/evaluation.py
from pathlib import Path
from datetime import date
from typing import Optional

from edps.config import load_config
from edps.core.llm import LLMClient


@dataclass
class EvaluationResult:
    """Result of section evaluation."""
    recall_score: int
    quiz_score: float
    recall_feedback: RecallFeedback
    quiz_feedback: QuizFeedback


def evaluate_section(
    section_path: Path,
    book_slug: str,
    section_id: str,
    config: Optional["EdpsConfig"] = None,
) -> EvaluationResult:
    """Evaluate a section's recall and quiz answers.

    Args:
        section_path: Path to the section directory
        book_slug: Book identifier
        section_id: Section identifier
        config: Optional config (loads default if not provided)

    Returns:
        EvaluationResult with scores and feedback
    """
    if config is None:
        config = load_config()

    # Find source file
    source_file = section_path / f"EDPS-{book_slug}-{section_id}.txt"
    if not source_file.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")

    source_text = source_file.read_text()

    # Read and parse recall
    recall_path = section_path / "recall.md"
    recall_raw = recall_path.read_text()
    recall_content = parse_recall_content(recall_raw)

    # Read and parse quiz
    quiz_path = section_path / "quiz.md"
    quiz_raw = quiz_path.read_text()
    quiz_content = parse_quiz_content(quiz_raw)

    # Build prompt and call LLM
    prompt = build_evaluation_prompt(source_text, recall_content, quiz_content)

    client = LLMClient(config)
    response = client.complete(prompt, max_tokens=2000)

    # Parse response
    recall_feedback, quiz_feedback = parse_evaluation_response(response.content)

    # Format and append feedback
    eval_date = date.today().isoformat()
    source_name = source_file.name

    recall_md = format_recall_feedback(recall_feedback, eval_date, source_name)
    quiz_md = format_quiz_feedback(quiz_feedback, eval_date, source_name)

    # Append to files (avoid duplicate feedback)
    if "## AI Feedback" not in recall_raw:
        with open(recall_path, "a") as f:
            f.write(recall_md)

    if "## AI Feedback" not in quiz_raw:
        with open(quiz_path, "a") as f:
            f.write(quiz_md)

    return EvaluationResult(
        recall_score=recall_feedback.score,
        quiz_score=quiz_feedback.total_score,
        recall_feedback=recall_feedback,
        quiz_feedback=quiz_feedback,
    )
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestEvaluateSection -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add main evaluate_section function"
```

---

## Task 8: Add CLI Command

**Files:**
- Create: `tools/edps/commands/eval.py`
- Modify: `tools/edps/cli.py`

**Step 1: Create eval command**

```python
# tools/edps/commands/eval.py
"""Eval command - AI evaluation of homework."""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from edps.config import load_config
from edps.evaluation import evaluate_section
from edps.progress import update_progress, SectionStatus

console = Console()


def eval_cmd(
    book_slug: str = typer.Argument(..., help="Book slug (e.g., 'wealth-of-nations')"),
    section_id: str = typer.Argument(..., help="Section ID (e.g., '001')"),
    books_dir: Optional[Path] = typer.Option(
        None,
        help="Path to books directory",
    ),
) -> None:
    """Evaluate recall and quiz answers using AI."""
    if books_dir is None:
        books_dir = Path.cwd() / "books"

    section_path = books_dir / book_slug / "sections" / section_id

    if not section_path.exists():
        console.print(f"[red]Error:[/red] Section not found: {section_path}")
        raise typer.Exit(1)

    console.print(f"Evaluating {book_slug}/{section_id}...")

    try:
        config = load_config()
        result = evaluate_section(section_path, book_slug, section_id, config)

        # Update progress.yaml with AI scores
        book_path = books_dir / book_slug
        update_progress(book_path, {
            section_id: SectionStatus(
                is_complete=True,
                recall_score=result.recall_score,
                quiz_score=result.quiz_score,
            )
        })

        console.print(f"\n[green]✓[/green] Evaluation complete!")
        console.print(f"  Recall: {result.recall_score}/5")
        console.print(f"  Quiz: {result.quiz_score}/8")
        console.print(f"\nFeedback appended to recall.md and quiz.md")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Evaluation failed: {e}")
        raise typer.Exit(1)
```

**Step 2: Register command in cli.py**

```python
# Modify tools/edps/cli.py - add import and registration
from edps.commands.eval import eval_cmd as eval_command

# Add after other app.command() calls:
app.command(name="eval")(eval_command)
```

**Step 3: Test manually**

Run: `PYTHONPATH="$PWD/tools" python -m edps.cli eval --help`
Expected: Shows help for eval command

**Step 4: Commit**

```bash
git add tools/edps/commands/eval.py tools/edps/cli.py
git commit -m "feat(eval): add edps eval CLI command"
```

---

## Task 9: Update Pre-commit Hook

**Files:**
- Modify: `tools/edps/commands/hooks.py`
- Modify: `tools/edps/progress.py`

**Step 1: Update hook script to call evaluation**

```python
# Modify tools/edps/commands/hooks.py - update HOOK_SCRIPT

HOOK_SCRIPT = '''#!/bin/bash
set -e

# Get staged files
STAGED=$(git diff --cached --name-only)

if [ -z "$STAGED" ]; then
    exit 0
fi

# Run progress sync and evaluation on staged files
MODIFIED=$(python -m edps.progress --hook --eval <<< "$STAGED" 2>/dev/null || true)

# Auto-stage any modified files (progress.yaml, recall.md, quiz.md)
if [ -n "$MODIFIED" ]; then
    echo "$MODIFIED" | while read -r file; do
        if [ -n "$file" ] && [ -f "$file" ]; then
            git add "$file"
            echo "Auto-staged: $file"
        fi
    done
fi
'''
```

**Step 2: Update progress.py main() to support --eval flag**

```python
# Modify tools/edps/progress.py - update main() function

def main():
    """CLI entry point for hook mode."""
    import sys

    if "--hook" in sys.argv:
        do_eval = "--eval" in sys.argv

        # Read staged files from stdin
        staged = sys.stdin.read().strip().split("\n")
        staged = [f for f in staged if f]  # Remove empty lines

        modified = run_hook(staged, do_eval=do_eval)

        # Print modified files for the hook to stage
        for path in modified:
            print(path)
```

**Step 3: Update run_hook to support evaluation**

```python
# Modify tools/edps/progress.py - update run_hook signature and logic

def run_hook(staged_files: list[str], base_path: Path = None, do_eval: bool = False) -> list[Path]:
    """
    Main hook entry point.

    Args:
        staged_files: List of staged file paths
        base_path: Base path of repository
        do_eval: Whether to run AI evaluation

    Returns:
        List of modified file paths (for auto-staging)
    """
    if base_path is None:
        base_path = Path.cwd()

    affected = parse_staged_files(staged_files)

    if not affected:
        return []

    modified_files = []

    for book_slug, section_ids in affected.items():
        book_path = base_path / "books" / book_slug

        if not book_path.exists():
            continue

        section_updates = {}
        for section_id in section_ids:
            section_path = book_path / "sections" / section_id
            if section_path.exists():
                status = check_section_completion(section_path)

                # Run AI evaluation if section is complete and eval requested
                if status.is_complete and do_eval:
                    try:
                        from edps.evaluation import evaluate_section
                        from edps.config import load_config

                        config = load_config()
                        result = evaluate_section(section_path, book_slug, section_id, config)

                        # Override scores with AI scores
                        status = SectionStatus(
                            is_complete=True,
                            recall_score=result.recall_score,
                            quiz_score=result.quiz_score,
                        )

                        # Add recall.md and quiz.md to modified files
                        modified_files.append(section_path / "recall.md")
                        modified_files.append(section_path / "quiz.md")

                    except Exception as e:
                        # Log but don't fail the commit
                        import sys
                        print(f"Warning: Evaluation failed for {section_id}: {e}", file=sys.stderr)

                section_updates[section_id] = status

        if section_updates:
            update_progress(book_path, section_updates)
            modified_files.append(book_path / "progress.yaml")

    return modified_files
```

**Step 4: Commit**

```bash
git add tools/edps/commands/hooks.py tools/edps/progress.py
git commit -m "feat(eval): integrate evaluation into pre-commit hook"
```

---

## Task 10: Add Model Config for Evaluation

**Files:**
- Modify: `tools/edps/config.py`

**Step 1: Add evaluation model to config**

```python
# Modify tools/edps/config.py - add to ModelsConfig

@dataclass
class ModelsConfig:
    """Per-task model overrides."""
    chunking: str = "claude-sonnet-4-20250514"
    summary: str = "claude-sonnet-4-20250514"
    podcast: str = "claude-sonnet-4-20250514"
    quiz: str = "claude-haiku-3-5"
    claims_synthesis: str = "claude-sonnet-4-20250514"
    evaluation: str = "claude-sonnet-4-20250514"  # Add this line
```

**Step 2: Update load_config to include evaluation model**

```python
# In load_config(), add to models loading:
evaluation=models_data.get("evaluation", config.models.evaluation),
```

**Step 3: Update evaluate_section to use model config**

```python
# Modify tools/edps/evaluation.py - update LLM call
response = client.complete(prompt, model=config.models.evaluation, max_tokens=2000)
```

**Step 4: Commit**

```bash
git add tools/edps/config.py tools/edps/evaluation.py
git commit -m "feat(eval): add configurable evaluation model"
```

---

## Task 11: Update Progress Schema for Float Scores

**Files:**
- Modify: `tools/edps/progress.py`

**Step 1: Update SectionStatus to support float quiz scores**

```python
# Modify tools/edps/progress.py - update SectionStatus dataclass

@dataclass
class SectionStatus:
    """Result of checking section completion."""
    is_complete: bool
    recall_score: Optional[int]
    quiz_score: Optional[float]  # Changed from Optional[int] to support 7.5
```

**Step 2: Update type hints in update_progress**

The existing code should handle floats already since YAML supports them.

**Step 3: Commit**

```bash
git add tools/edps/progress.py
git commit -m "feat(eval): support float quiz scores in progress"
```

---

## Task 12: Final Integration Test

**Files:**
- Test: `tests/test_evaluation.py`

**Step 1: Add integration test**

```python
# Add to tests/test_evaluation.py

class TestIntegration:
    """Integration tests for full evaluation flow."""

    def test_full_evaluation_flow(self, tmp_path):
        """Test complete flow from files to feedback."""
        # Setup
        book_path = tmp_path / "books" / "test-book"
        section_path = book_path / "sections" / "001"
        section_path.mkdir(parents=True)

        # Create source file
        (section_path / "EDPS-test-book-001.txt").write_text(
            "Division of labor increases productivity through three causes: "
            "dexterity, time savings, and machinery invention."
        )

        # Create recall file
        (section_path / "recall.md").write_text('''# Recall

## From Memory (before re-reading)

1. Division of labor increases productivity
2. Three causes explain this improvement

## One Sentence I'd Tell Someone

Division of labor is key to productivity.
''')

        # Create quiz file
        (section_path / "quiz.md").write_text('''# Quiz

### 1. Main Claim

What increases productivity?

**Answer:** Division of labor
''')

        # Create progress file
        (book_path / "progress.yaml").write_text("completed_sections: []\nquiz_scores: {}\nrecall_scores: {}\nstats: {}")

        with patch("edps.evaluation.LLMClient") as mock_client:
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

            # Verify result
            assert result.recall_score == 5
            assert result.quiz_score == 8

            # Verify files were updated
            recall_content = (section_path / "recall.md").read_text()
            quiz_content = (section_path / "quiz.md").read_text()

            assert "## AI Feedback" in recall_content
            assert "### AI Score: 5 / 5" in recall_content
            assert "## AI Feedback" in quiz_content
            assert "### AI Score: 8 / 8" in quiz_content
```

**Step 2: Run all tests**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_evaluation.py
git commit -m "test(eval): add full integration test"
```

---

## Task 13: Reinstall Hook

**Step 1: Reinstall hook with new script**

Run: `edps init-hooks --force`
Expected: Hook installed with evaluation support

**Step 2: Commit hook update documentation**

```bash
git add docs/plans/2025-12-25-ai-evaluation-implementation.md
git commit -m "docs: complete AI evaluation implementation plan"
```

---

## Summary

After completing all tasks, you will have:

1. `tools/edps/evaluation.py` - Core evaluation logic
2. `tools/edps/commands/eval.py` - CLI command
3. Updated pre-commit hook with `--eval` flag
4. `tests/test_evaluation.py` - Comprehensive tests
5. Config support for evaluation model

**Usage:**

```bash
# Manual evaluation
edps eval wealth-of-nations 001

# Automatic (via pre-commit hook)
git add books/wealth-of-nations/sections/001/recall.md quiz.md
git commit -m "Complete section 001"
# → AI evaluation runs automatically
# → Feedback appended to files
# → progress.yaml updated with AI scores
```
