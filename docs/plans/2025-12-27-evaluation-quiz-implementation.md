# Evaluation & Quiz Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform terse 30-second evaluation into 3-minute learning experience; add variable MCQ+prose quiz format with hard questions.

**Architecture:** Extend existing dataclasses with new fields (accuracy, reasoning, writing per answer; thematic insights; tutor's note). Update prompts to request expanded JSON. Update formatters to output new markdown structure. Quiz generation becomes variable-format with MCQ support.

**Tech Stack:** Python, pytest, ruamel.yaml, existing LLM client infrastructure

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
            label="Q1: Main Claim",
            correct=True,
            note="Legacy note",
            score=1.0,
            accuracy="Correct—identified propensity to exchange as origin.",
            reasoning="Causal chain is sound.",
            writing="Consider 'propensity' over 'innate need'.",
        )
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
    label: str
    correct: bool
    note: str
    score: Optional[float] = None  # For quiz questions
    accuracy: Optional[str] = None  # Factual correctness analysis
    reasoning: Optional[str] = None  # Logic and argument analysis
    writing: Optional[str] = None  # Prose quality analysis
```

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
@dataclass
class QuizFeedback:
    """Complete feedback for quiz.md evaluation."""
    answers: list[AnswerFeedback]
    total_score: float
    reasoning: str  # Legacy field, kept for backward compat
    thematic_insights: Optional[ThematicInsights] = None
    tutors_note: Optional[str] = None
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

## Phase 2: Updated Evaluation Prompt

### Task 2.1: Create Expanded Prompt Builder

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
        from edps.quiz_types import MCQuestion

        q = MCQuestion(
            number=1,
            question="Which assumptions does Smith's argument depend on?",
            options=[
                ("A", "Humans are rational", True),
                ("B", "Exchange is possible", True),
                ("C", "Government enforces contracts", False),
                ("D", "Surplus is feasible", True),
            ],
            answer_type="multiple",
        )
        assert q.answer_type == "multiple"
        assert q.correct_count() == 3

    def test_mcq_can_have_no_answer(self):
        """MCQ should support none-correct option."""
        from edps.quiz_types import MCQuestion

        q = MCQuestion(
            number=2,
            question="Which would disprove Smith's thesis?",
            options=[
                ("A", "Option that doesn't disprove", False),
                ("B", "Another non-disproof", False),
                ("C", "Still not a disproof", False),
                ("D", "Nope", False),
            ],
            answer_type="none",
        )
        assert q.answer_type == "none"
        assert q.correct_count() == 0
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
class MCQuestion:
    """Multiple choice question with variable answer types."""
    number: int
    question: str
    options: list[tuple[str, str, bool]]  # (letter, text, is_correct)
    answer_type: Literal["one", "multiple", "none"]

    def correct_count(self) -> int:
        return sum(1 for _, _, correct in self.options if correct)


@dataclass
class ProseQuestion:
    """Prose question with variable types."""
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
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

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

**Steps 2-5:** Implement parsing, test, commit.

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

### Task 5.2: Update Config for Longer Outputs

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

### Task 5.3: Update README

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
