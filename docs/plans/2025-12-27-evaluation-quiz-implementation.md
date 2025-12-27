# Evaluation & Quiz Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform terse 30-second evaluation into 3-minute learning experience; add variable MCQ+prose quiz format with hard questions.

**Architecture:** Extend existing dataclasses with new fields (accuracy, reasoning, writing per answer; thematic insights; tutor's note). Update prompts to request expanded JSON. Update formatters to output new markdown structure. Quiz generation becomes variable-format with MCQ support.

**Tech Stack:** Python, pytest, hypothesis, ruamel.yaml, existing LLM client infrastructure

---

### Enhancements from Code Review (2025-12-27)

This plan incorporates feedback from architectural review:

| Enhancement | Task | Description |
|-------------|------|-------------|
| **Schema versioning** | 1.3, 1.4 | `schema_version: Literal["v0","v1"]` + `migrate_v0_to_v1()` |
| **Field renaming** | 1.1 | `note` → `explanation`, add `question_id` |
| **MCOption dataclass** | 4.1 | Replace brittle tuples with structured `MCOption` |
| **Answer validation** | 4.1 | `__post_init__` validates `answer_type` matches correct options |
| **F1 scoring** | 4.3 | Precision × Recall for fair partial credit |
| **Two-pass prompting** | 2.1 | Architecture note for future enhancement |
| **Property-based tests** | 5.2 | Hypothesis tests for scoring invariants |

---

## Phase 1: Expanded Evaluation Dataclasses

### Task 1.1: Add Per-Answer Detail Fields

**Files:**
- Modify: `tools/edps/evaluation.py:10-17`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

Add to `tests/test_evaluation.py`:

```python
class TestExpandedAnswerFeedback:
    """Tests for expanded answer feedback with accuracy/reasoning/writing."""

    def test_answer_feedback_has_accuracy_field(self):
        """AnswerFeedback should have accuracy analysis."""
        from edps.evaluation import AnswerFeedback
        feedback = AnswerFeedback(
            question_id="q1",
            label="Q1: Main Claim",
            correct=True,
            explanation="Legacy note",
            score=1.0,
            accuracy="Correct—identified propensity to exchange as origin.",
            reasoning="Causal chain is sound.",
            writing="Consider 'propensity' over 'innate need'.",
        )
        assert feedback.question_id == "q1"
        assert feedback.accuracy == "Correct—identified propensity to exchange as origin."
        assert feedback.reasoning == "Causal chain is sound."
        assert feedback.writing == "Consider 'propensity' over 'innate need'."
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedAnswerFeedback -v`
Expected: FAIL with "TypeError: unexpected keyword argument 'accuracy'"

**Step 3: Write minimal implementation**

In `tools/edps/evaluation.py`, update `AnswerFeedback`:

```python
@dataclass
class AnswerFeedback:
    """Feedback for a single answer or recall point."""
    question_id: str  # Stable identifier (e.g., "q1", "recall_main")
    label: str  # Display label (e.g., "Q1: Main Claim")
    correct: bool
    explanation: str  # Replaces ambiguous "note"
    score: Optional[float] = None  # For quiz questions
    accuracy: Optional[str] = None  # Factual correctness analysis
    reasoning: Optional[str] = None  # Logic and argument analysis
    writing: Optional[str] = None  # Prose quality analysis
```

**Note:** `question_id` enables cross-references in thematic insights. `explanation` replaces `note` for clarity.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedAnswerFeedback -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add accuracy/reasoning/writing fields to AnswerFeedback"
```

---

### Task 1.2: Add Thematic Insights Dataclass

**Files:**
- Modify: `tools/edps/evaluation.py` (after line 35)
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestThematicInsights -v`
Expected: FAIL with "cannot import name 'ThematicInsights'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py` after `QuizFeedback`:

```python
@dataclass
class WritingScores:
    """Writing craft scores (1-5 each)."""
    precision: int
    clarity: int
    economy: int
    suggestion: str  # One concrete fix to practice


@dataclass
class ThematicInsights:
    """Cross-answer thematic patterns."""
    source_mastery: str
    reasoning_quality: str
    writing_craft: WritingScores
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestThematicInsights -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add ThematicInsights and WritingScores dataclasses"
```

---

### Task 1.3: Add Tutor's Note and Update Feedback Classes

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedFeedback -v`
Expected: FAIL with "TypeError: unexpected keyword argument 'thematic_insights'"

**Step 3: Write minimal implementation**

Update `QuizFeedback` in `tools/edps/evaluation.py`:

```python
from typing import Literal

@dataclass
class QuizFeedback:
    """Complete feedback for quiz.md evaluation."""
    schema_version: Literal["v0", "v1"] = "v1"  # Version for migration support
    answers: list[AnswerFeedback]
    total_score: float
    reasoning: str  # Legacy field, kept for backward compat
    thematic_insights: Optional[ThematicInsights] = None
    tutors_note: Optional[str] = None
    model_id: Optional[str] = None  # Which LLM produced this evaluation
    created_at: Optional[str] = None  # ISO timestamp
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedFeedback -v`
Expected: PASS

**Step 5: Run all evaluation tests to ensure backward compat**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add thematic_insights and tutors_note to QuizFeedback"
```

---

### Task 1.4: Add Schema Migration Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestSchemaMigration -v`
Expected: FAIL with "cannot import name 'migrate_v0_to_v1'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py`:

```python
def migrate_v0_to_v1(data: dict) -> dict:
    """Migrate v0 evaluation schema to v1.

    Changes:
    - Adds schema_version: "v1"
    - Maps 'note' -> 'explanation'
    - Adds question_id from label or index
    """
    # Check if already v1
    if data.get("quiz", {}).get("schema_version") == "v1":
        return data

    result = {"recall": data.get("recall", {}), "quiz": {}}
    quiz = data.get("quiz", {})

    # Migrate answers
    migrated_answers = []
    for i, answer in enumerate(quiz.get("answers", [])):
        migrated = {
            "question_id": f"q{i+1}",
            "label": answer.get("label", f"Q{i+1}"),
            "correct": answer.get("correct", False),
            "explanation": answer.get("note", ""),  # note -> explanation
            "score": answer.get("score"),
            "accuracy": answer.get("accuracy"),
            "reasoning": answer.get("reasoning"),
            "writing": answer.get("writing"),
        }
        migrated_answers.append(migrated)

    result["quiz"] = {
        "schema_version": "v1",
        "answers": migrated_answers,
        "total_score": quiz.get("total_score", 0),
        "reasoning": quiz.get("reasoning", ""),
        "thematic_insights": quiz.get("thematic_insights"),
        "tutors_note": quiz.get("tutors_note"),
    }

    return result
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestSchemaMigration -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): add migrate_v0_to_v1 for schema versioning"
```

---

## Phase 2: Updated Evaluation Prompt

### Task 2.1: Create Expanded Prompt Builder

**Architecture Note: Two-Pass Strategy (from code review)**

For more reliable parsing, consider a two-pass approach:
1. **Pass 1:** Request JSON-only response with structured scores and concise explanations
2. **Pass 2:** If tutors_note needed, request narrative referencing the already-parsed JSON

This reduces parse failures and keeps narratives separate from structured data. For initial implementation, we use single-pass with validation + repair loop (simpler). Future enhancement: split into two calls.

**Prompt Design Principles:**
- Embed compact JSON contract, not verbose schema
- Include one minimal example + one edge case
- Instruct: "return booleans as true/false, no trailing commas"
- Keep per-answer explanations to 1-3 sentences; depth goes in tutors_note

**Files:**
- Modify: `tools/edps/evaluation.py:112-193`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedEvaluationPrompt -v`
Expected: FAIL (current prompt doesn't include these)

**Step 3: Write minimal implementation**

Replace the prompt construction in `build_evaluation_prompt()`. The new prompt template:

```python
    prompt += """
# Evaluation Task

Provide comprehensive feedback on the student's work. Return as JSON:

```json
{
  "recall": {
    "points": [
      {
        "label": "Point description",
        "correct": true/false,
        "note": "Brief note (legacy)",
        "accuracy": "What they got right/wrong factually",
        "reasoning": "How their logic holds up",
        "writing": "Prose quality feedback with specific suggestions"
      }
    ],
    "one_sentence_ok": true/false,
    "one_sentence_note": "Feedback on summary",
    "score": 0-5,
    "reasoning": "Overall assessment"
  },
  "quiz": {
    "answers": [
      {
        "label": "Q1: Title",
        "correct": true/false,
        "score": 0-1,
        "note": "Brief note (legacy)",
        "accuracy": "Factual correctness analysis",
        "reasoning": "Logic and argument analysis",
        "writing": "Prose quality: precision, clarity, economy"
      }
    ],
    "total_score": 0-8,
    "reasoning": "Legacy overall assessment",
    "thematic_insights": {
      "source_mastery": "Patterns across answers—what they consistently get/miss. Cite specific examples.",
      "reasoning_quality": "How they build arguments. Logical gaps. Strengths. Edges to develop.",
      "writing_craft": {
        "precision": 1-5,
        "clarity": 1-5,
        "economy": 1-5,
        "suggestion": "One concrete fix to practice"
      }
    },
    "tutors_note": "Narrative synthesis (3-4 paragraphs): What they're doing well, 2-3 things to carry forward with depth, prompt for next section."
  }
}
```

## Scoring & Feedback Guidelines

**Per-Answer Analysis:**
- **Accuracy:** Did they capture what the source actually says? Quote specifics.
- **Reasoning:** Is their causal logic sound? Do they identify correct relationships?
- **Writing:**
  - Precision: Do they use the author's key terms correctly?
  - Clarity: Do they lead with main points? Is structure clear?
  - Economy: Can they say it in fewer words without losing meaning?

**Thematic Insights:**
- Identify PATTERNS across all answers, not just per-question issues
- Be specific: "You wrote X but Smith says Y" not "some inaccuracies"

**Tutor's Note:**
- Open with genuine praise backed by evidence
- Give 2-3 actionable insights with depth (why it matters, how to apply)
- Close with what to watch for in the next section

Respond ONLY with the JSON object, no other text."""
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedEvaluationPrompt -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): update prompt to request expanded feedback format"
```

---

### Task 2.2: Update Response Parser

**Files:**
- Modify: `tools/edps/evaluation.py:196-256`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedResponseParsing -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Update `parse_evaluation_response()` to handle new fields:

```python
def parse_evaluation_response(response: str) -> tuple[RecallFeedback, QuizFeedback]:
    """Parse JSON from LLM evaluation response."""
    # Extract JSON (existing logic)
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r'(\{.*\})', response, re.DOTALL)
        json_str = json_match.group(1) if json_match else response

    data = json.loads(json_str)

    # Build RecallFeedback with optional new fields
    recall_data = data["recall"]
    recall_points = [
        AnswerFeedback(
            label=p["label"],
            correct=p["correct"],
            note=p["note"],
            accuracy=p.get("accuracy"),
            reasoning=p.get("reasoning"),
            writing=p.get("writing"),
        )
        for p in recall_data["points"]
    ]
    recall_feedback = RecallFeedback(
        points=recall_points,
        one_sentence_ok=recall_data["one_sentence_ok"],
        one_sentence_note=recall_data["one_sentence_note"],
        score=recall_data["score"],
        reasoning=recall_data["reasoning"],
    )

    # Build QuizFeedback with optional new fields
    quiz_data = data["quiz"]
    quiz_answers = [
        AnswerFeedback(
            label=a["label"],
            correct=a["correct"],
            note=a["note"],
            score=a["score"],
            accuracy=a.get("accuracy"),
            reasoning=a.get("reasoning"),
            writing=a.get("writing"),
        )
        for a in quiz_data["answers"]
    ]

    # Parse thematic insights if present
    thematic_insights = None
    if "thematic_insights" in quiz_data:
        ti = quiz_data["thematic_insights"]
        wc = ti["writing_craft"]
        thematic_insights = ThematicInsights(
            source_mastery=ti["source_mastery"],
            reasoning_quality=ti["reasoning_quality"],
            writing_craft=WritingScores(
                precision=wc["precision"],
                clarity=wc["clarity"],
                economy=wc["economy"],
                suggestion=wc["suggestion"],
            ),
        )

    quiz_feedback = QuizFeedback(
        answers=quiz_answers,
        total_score=quiz_data["total_score"],
        reasoning=quiz_data["reasoning"],
        thematic_insights=thematic_insights,
        tutors_note=quiz_data.get("tutors_note"),
    )

    return recall_feedback, quiz_feedback
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedResponseParsing -v`
Expected: PASS

**Step 5: Run all tests to ensure backward compat**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): parse expanded feedback with thematic insights and tutor's note"
```

---

## Phase 3: Updated Markdown Formatter

### Task 3.1: Create Expanded Quiz Feedback Formatter

**Files:**
- Modify: `tools/edps/evaluation.py:303-342`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedMarkdownFormat -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace `format_quiz_feedback()`:

```python
def format_quiz_feedback(feedback: QuizFeedback, eval_date: str, source_file: str) -> str:
    """Format quiz feedback as expanded markdown."""
    lines = [
        "---",
        "",
        "## AI Feedback",
        "",
        f"**Evaluated:** {eval_date} | **Source:** {source_file}",
        f"**Total Score:** {feedback.total_score}/8",
        "",
        "---",
        "",
        "### Per-Answer Analysis",
        "",
    ]

    for answer in feedback.answers:
        status = "✓" if answer.correct else "⚠️"
        score_str = f"{answer.score:.1f}/1.0" if answer.score is not None else ""
        lines.append(f"#### {answer.label} ({score_str}) {status}")
        lines.append("")

        if answer.accuracy:
            lines.append(f"**Accuracy:** {answer.accuracy}")
        if answer.reasoning:
            lines.append(f"**Reasoning:** {answer.reasoning}")
        if answer.writing:
            lines.append(f"**Writing:** {answer.writing}")

        # Fallback to legacy note if no expanded fields
        if not (answer.accuracy or answer.reasoning or answer.writing):
            lines.append(f"**Feedback:** {answer.note}")

        lines.append("")

    # Thematic insights
    if feedback.thematic_insights:
        ti = feedback.thematic_insights
        wc = ti.writing_craft
        lines.extend([
            "---",
            "",
            "### Thematic Insights",
            "",
            "#### Source Mastery",
            ti.source_mastery,
            "",
            "#### Reasoning Quality",
            ti.reasoning_quality,
            "",
            "#### Writing Craft",
            f"**Precision:** {wc.precision}/5 | **Clarity:** {wc.clarity}/5 | **Economy:** {wc.economy}/5",
            "",
            f"**Practice:** {wc.suggestion}",
            "",
        ])

    # Tutor's note
    if feedback.tutors_note:
        lines.extend([
            "---",
            "",
            "### Tutor's Note",
            "",
            feedback.tutors_note,
        ])

    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestExpandedMarkdownFormat -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(eval): format expanded feedback with per-answer analysis and tutor's note"
```

---

### Task 3.2: Update Recall Feedback Formatter (Similar Pattern)

**Files:**
- Modify: `tools/edps/evaluation.py:258-301`
- Test: `tests/test_evaluation.py`

Follow same pattern as Task 3.1 for `format_recall_feedback()`.

**Step 1-5:** Similar to Task 3.1, adapted for recall structure.

**Commit:**
```bash
git commit -m "feat(eval): format expanded recall feedback"
```

---

## Phase 4: Quiz Generation Redesign

### Task 4.1: Create MCQ Question Types

**Files:**
- Create: `tools/edps/quiz_types.py`
- Test: `tests/test_quiz_types.py`

**Step 1: Write the failing test**

Create `tests/test_quiz_types.py`:

```python
"""Tests for quiz question type definitions."""

class TestMCQTypes:
    """Tests for multiple choice question types."""

    def test_mcq_can_have_multiple_answers(self):
        """MCQ should support multiple correct answers."""
        from edps.quiz_types import MCQuestion, MCOption

        q = MCQuestion(
            question_id="mcq1",
            number=1,
            question="Which assumptions does Smith's argument depend on?",
            options=[
                MCOption("A", "Humans are rational", True),
                MCOption("B", "Exchange is possible", True),
                MCOption("C", "Government enforces contracts", False),
                MCOption("D", "Surplus is feasible", True),
            ],
            answer_type="multiple",
        )
        assert q.answer_type == "multiple"
        assert q.correct_count() == 3
        assert q.correct_letters() == {"A", "B", "D"}

    def test_mcq_can_have_no_answer(self):
        """MCQ should support none-correct option."""
        from edps.quiz_types import MCQuestion, MCOption

        q = MCQuestion(
            question_id="mcq2",
            number=2,
            question="Which would disprove Smith's thesis?",
            options=[
                MCOption("A", "Option that doesn't disprove", False),
                MCOption("B", "Another non-disproof", False),
                MCOption("C", "Still not a disproof", False),
                MCOption("D", "Nope", False),
            ],
            answer_type="none",
        )
        assert q.answer_type == "none"
        assert q.correct_count() == 0

    def test_mcoption_validates_letter(self):
        """MCOption should validate letter is A-H."""
        from edps.quiz_types import MCOption
        import pytest

        with pytest.raises(ValueError):
            MCOption("Z", "Invalid letter", True)

    def test_mcq_validates_answer_type(self):
        """MCQuestion should validate answer_type matches options."""
        from edps.quiz_types import MCQuestion, MCOption
        import pytest

        # answer_type="one" but 2 correct answers
        with pytest.raises(ValueError):
            MCQuestion(
                question_id="mcq_bad",
                number=1,
                question="Bad question",
                options=[
                    MCOption("A", "Correct 1", True),
                    MCOption("B", "Correct 2", True),
                ],
                answer_type="one",
            )
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_quiz_types.py -v`
Expected: FAIL with "cannot import name 'MCQuestion'"

**Step 3: Write minimal implementation**

Create `tools/edps/quiz_types.py`:

```python
"""Quiz question type definitions."""
from dataclasses import dataclass
from typing import Literal


@dataclass
class MCOption:
    """Single option in a multiple choice question."""
    letter: str  # A, B, C, D
    text: str
    is_correct: bool

    def __post_init__(self):
        if len(self.letter) != 1 or self.letter not in "ABCDEFGH":
            raise ValueError(f"Invalid option letter: {self.letter}")


@dataclass
class MCQuestion:
    """Multiple choice question with variable answer types."""
    question_id: str  # Stable identifier (e.g., "mcq1")
    number: int  # Display number
    question: str
    options: list[MCOption]  # Structured options (not tuples)
    answer_type: Literal["one", "multiple", "none"]

    def correct_count(self) -> int:
        return sum(1 for opt in self.options if opt.is_correct)

    def correct_letters(self) -> set[str]:
        return {opt.letter for opt in self.options if opt.is_correct}

    def __post_init__(self):
        # Validate answer_type matches options
        correct = self.correct_count()
        if self.answer_type == "none" and correct != 0:
            raise ValueError("answer_type='none' but has correct options")
        if self.answer_type == "one" and correct != 1:
            raise ValueError(f"answer_type='one' but has {correct} correct options")


@dataclass
class ProseQuestion:
    """Prose question with variable types."""
    question_id: str  # Stable identifier
    number: int
    question: str
    question_type: Literal["adversarial", "comparative", "socratic", "synthesis"]
    sentence_range: tuple[int, int]  # (min, max) sentences
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_quiz_types.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/quiz_types.py tests/test_quiz_types.py
git commit -m "feat(quiz): add MCQuestion and ProseQuestion dataclasses"
```

---

### Task 4.2: Rewrite Quiz Generation Prompt

**Files:**
- Modify: `tools/edps/prompts/quiz.txt`

**Step 1: Backup existing prompt**

```bash
cp tools/edps/prompts/quiz.txt tools/edps/prompts/quiz.txt.bak
```

**Step 2: Write new prompt**

Replace `tools/edps/prompts/quiz.txt` with expanded variable-format prompt (see design doc for full prompt).

Key sections:
- Part A: Hard MCQs with one/multiple/none answer types
- Part B: Variable prose questions (Adversarial, Comparative, Socratic, Synthesis)
- Distribution logic based on section content type

**Step 3: Commit**

```bash
git add tools/edps/prompts/quiz.txt
git commit -m "feat(quiz): rewrite prompt for variable MCQ+prose format"
```

---

### Task 4.3: Update Quiz Parser for MCQ Support

**Files:**
- Modify: `tools/edps/evaluation.py` (add `parse_mcq_answers`)
- Modify: `tools/edps/quiz_types.py` (add `score_mcq_answer`)
- Test: `tests/test_evaluation.py`
- Test: `tests/test_quiz_types.py`

**Step 1: Write the failing test for parsing**

```python
class TestMCQParsing:
    """Tests for parsing MCQ answers from quiz.md."""

    def test_parses_mcq_with_multiple_answers(self):
        """Should parse MCQ with multiple selected answers."""
        from edps.evaluation import parse_quiz_content

        content = '''## Part A: Quick Recall

### 1.
Smith's argument depends on which assumption(s)?

- A) Humans are rational
- B) Exchange is possible
- C) Government enforces
- D) Surplus is feasible

**Select:** Multiple    **Answer(s):** A, B, D
'''
        result = parse_quiz_content(content)
        assert result["mcq_answers"][0]["selected"] == ["A", "B", "D"]
        assert result["mcq_answers"][0]["answer_type"] == "multiple"
```

**Step 2: Write failing test for F1 scoring**

Add to `tests/test_quiz_types.py`:

```python
class TestMCQScoring:
    """Tests for MCQ F1-based partial credit scoring."""

    def test_score_mcq_perfect_multiple(self):
        """Perfect match on multiple-answer MCQ should score 1.0."""
        from edps.quiz_types import score_mcq_answer

        gold = {"A", "B", "D"}  # Correct answers
        selected = {"A", "B", "D"}  # Student selected
        score = score_mcq_answer(gold, selected)
        assert score == 1.0

    def test_score_mcq_partial_credit(self):
        """Partial match should use F1 formula."""
        from edps.quiz_types import score_mcq_answer

        gold = {"A", "B", "D"}  # 3 correct
        selected = {"A", "B"}  # 2 selected, both correct
        # Precision = 2/2 = 1.0, Recall = 2/3 = 0.667
        # F1 = 2 * 1.0 * 0.667 / (1.0 + 0.667) = 0.8
        score = score_mcq_answer(gold, selected)
        assert abs(score - 0.8) < 0.01

    def test_score_mcq_with_wrong_selection(self):
        """Wrong selections should reduce precision."""
        from edps.quiz_types import score_mcq_answer

        gold = {"A", "B"}  # 2 correct
        selected = {"A", "C"}  # 1 right, 1 wrong
        # Precision = 1/2 = 0.5, Recall = 1/2 = 0.5
        # F1 = 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.5
        score = score_mcq_answer(gold, selected)
        assert abs(score - 0.5) < 0.01

    def test_score_mcq_none_correct_type(self):
        """'None of the above' case: selecting nothing is correct."""
        from edps.quiz_types import score_mcq_answer

        gold = set()  # No correct answers
        selected = set()  # Student correctly selected none
        score = score_mcq_answer(gold, selected)
        assert score == 1.0

    def test_score_mcq_none_but_selected(self):
        """'None' type but student selected something: 0."""
        from edps.quiz_types import score_mcq_answer

        gold = set()  # No correct answers
        selected = {"A"}  # Student wrongly selected A
        score = score_mcq_answer(gold, selected)
        assert score == 0.0

    def test_score_mcq_single_answer(self):
        """Single-answer MCQ: 1 if correct, 0 otherwise."""
        from edps.quiz_types import score_mcq_answer

        gold = {"B"}
        assert score_mcq_answer(gold, {"B"}) == 1.0
        assert score_mcq_answer(gold, {"A"}) == 0.0
        assert score_mcq_answer(gold, {"A", "B"}) < 1.0  # Over-selected
```

**Step 3: Implement F1 scoring function**

Add to `tools/edps/quiz_types.py`:

```python
def score_mcq_answer(gold: set[str], selected: set[str]) -> float:
    """Score MCQ answer using F1-based partial credit.

    Args:
        gold: Set of correct answer letters (e.g., {"A", "B", "D"})
        selected: Set of student's selected letters

    Returns:
        Score from 0.0 to 1.0 based on F1 formula.

    Scoring rules:
    - If both sets empty (none-of-the-above correct): 1.0
    - If gold empty but student selected: 0.0
    - Otherwise: F1 = 2*P*R / (P+R) where:
      - Precision P = |gold ∩ selected| / |selected|
      - Recall R = |gold ∩ selected| / |gold|
    """
    # Handle none-of-the-above case
    if not gold and not selected:
        return 1.0
    if not gold and selected:
        return 0.0
    if gold and not selected:
        return 0.0

    # Calculate F1
    intersection = gold & selected
    precision = len(intersection) / len(selected)
    recall = len(intersection) / len(gold)

    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return round(f1, 3)
```

**Step 4: Run tests**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_quiz_types.py::TestMCQScoring -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/quiz_types.py tools/edps/evaluation.py tests/test_quiz_types.py tests/test_evaluation.py
git commit -m "feat(quiz): add F1-based partial credit scoring for MCQs"
```

---

## Phase 5: Integration and Testing

### Task 5.1: End-to-End Test with Real Section

**Files:**
- Test: `tests/test_evaluation.py`

**Step 1: Write integration test**

```python
class TestExpandedEvaluationIntegration:
    """Integration test for full expanded evaluation."""

    def test_full_expanded_evaluation_flow(self, tmp_path):
        """Test complete flow produces ~800 word feedback."""
        # Setup test files
        # Mock LLM with expanded response
        # Verify output length and structure
        pass
```

**Step 2: Run on section 002**

```bash
PYTHONPATH="$PWD/tools" python -m edps.cli eval wealth-of-nations 002
```

**Step 3: Verify output matches design spec**

- [ ] Per-answer analysis with Accuracy/Reasoning/Writing
- [ ] Thematic insights section
- [ ] Tutor's note section
- [ ] ~800-1000 words total

**Step 4: Commit**

```bash
git commit -m "test(eval): add integration test for expanded evaluation"
```

---

### Task 5.2: Add Property-Based Tests (from code review)

**Rationale:** Property-based tests catch edge cases that unit tests miss. Use Hypothesis to generate random inputs and verify invariants.

**Files:**
- Create: `tests/test_properties.py`
- Modify: `pyproject.toml` (add hypothesis dependency)

**Step 1: Add Hypothesis dependency**

```bash
pip install hypothesis
# Add to pyproject.toml: hypothesis>=6.0
```

**Step 2: Write property-based tests for scoring**

```python
"""Property-based tests for scoring and parsing."""
from hypothesis import given, strategies as st, assume
from edps.quiz_types import score_mcq_answer


class TestMCQScoringProperties:
    """Property-based tests for MCQ scoring invariants."""

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=0, max_size=4),
        selected=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=0, max_size=4),
    )
    def test_score_always_between_0_and_1(self, gold, selected):
        """Score should always be in [0, 1] range."""
        score = score_mcq_answer(set(gold), set(selected))
        assert 0.0 <= score <= 1.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
    )
    def test_perfect_match_scores_1(self, gold):
        """Selecting exactly the correct answers should score 1.0."""
        score = score_mcq_answer(set(gold), set(gold))
        assert score == 1.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
        wrong=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=4),
    )
    def test_no_overlap_scores_0(self, gold, wrong):
        """Selecting only wrong answers should score 0."""
        assume(not (gold & wrong))  # Ensure no overlap
        score = score_mcq_answer(set(gold), set(wrong))
        assert score == 0.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=2, max_size=4),
    )
    def test_partial_selection_less_than_perfect(self, gold):
        """Selecting a subset of correct answers should score < 1.0."""
        partial = set(list(gold)[:-1])  # Remove one
        assume(len(partial) >= 1)
        score = score_mcq_answer(set(gold), partial)
        assert score < 1.0

    @given(
        gold=st.frozensets(st.sampled_from(list("ABCDEFGH")), min_size=1, max_size=3),
    )
    def test_adding_correct_increases_score(self, gold):
        """Adding a correct answer should not decrease score."""
        gold_list = list(gold)
        for i in range(len(gold_list)):
            partial = set(gold_list[:i+1])
            next_partial = set(gold_list[:i+2]) if i+2 <= len(gold_list) else set(gold)
            score1 = score_mcq_answer(set(gold), partial)
            score2 = score_mcq_answer(set(gold), next_partial)
            assert score2 >= score1 - 0.001  # Allow tiny float error
```

**Step 3: Write property tests for schema validation**

```python
@given(
    version=st.sampled_from(["v0", "v1"]),
    num_answers=st.integers(min_value=1, max_value=10),
)
def test_migration_preserves_answer_count(self, version, num_answers):
    """Migration should preserve the number of answers."""
    from edps.evaluation import migrate_v0_to_v1

    v0_data = {
        "quiz": {
            "answers": [{"label": f"Q{i}", "correct": True, "note": "OK", "score": 1.0}
                        for i in range(num_answers)],
            "total_score": num_answers,
            "reasoning": "Good"
        }
    }

    v1_data = migrate_v0_to_v1(v0_data)
    assert len(v1_data["quiz"]["answers"]) == num_answers
```

**Step 4: Run property tests**

```bash
PYTHONPATH="$PWD/tools" python -m pytest tests/test_properties.py -v
```

**Step 5: Commit**

```bash
git add tests/test_properties.py pyproject.toml
git commit -m "test: add property-based tests for scoring and schema"
```

---

### Task 5.3: Update Config for Longer Outputs

**Files:**
- Modify: `tools/edps/config.py`

**Step 1: Increase max_tokens default**

```python
@dataclass
class DefaultsConfig:
    temperature: float = 0.3
    max_tokens: int = 8192  # Increased from 4096 for expanded feedback
    confirm_before_call: bool = True
```

**Step 2: Commit**

```bash
git add tools/edps/config.py
git commit -m "config: increase max_tokens for expanded evaluation output"
```

---

### Task 5.4: Update README

**Files:**
- Modify: `README.md`

Document new evaluation and quiz format. Add example output.

**Commit:**

```bash
git commit -m "docs: document expanded evaluation and quiz format"
```

---

## Success Checklist

- [ ] Evaluation output is 800-1000 words
- [ ] Each answer gets Accuracy/Reasoning/Writing feedback
- [ ] Thematic insights identify patterns across answers
- [ ] Tutor's note provides actionable forward-looking advice
- [ ] All existing tests pass (backward compat)
- [ ] Quiz includes hard MCQs with multi/none-answer options
- [ ] Prose questions vary by type
- [ ] Schema versioning with `migrate_v0_to_v1()` works correctly
- [ ] MCOption dataclass validates letter and answer_type consistency
- [ ] F1 scoring gives fair partial credit for multi-answer MCQs
- [ ] Property-based tests verify scoring invariants
