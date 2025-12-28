# Inline Claim-Level Feedback Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move AI feedback inline with specific errors in user's answers, using collapsible `<details>` sections.

**Architecture:** Parse LLM response for claim-level errors with quoted text anchors. Strip old feedback, inject new annotations after exact text matches, append writing notes per-answer, and add slimmed-down summary at end.

**Tech Stack:** Python, pytest, regex for markdown parsing, difflib for fuzzy matching fallback

---

## Task 1: Add InlineError Dataclass

**Files:**
- Modify: `tools/edps/assessment.py` (currently named `evaluation.py`)
- Test: `tests/test_assessment.py` (currently named `test_evaluation.py`)

**Step 1: Write the failing test**

Add to `tests/test_evaluation.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInlineErrorDataclass -v`
Expected: FAIL with "cannot import name 'InlineError'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py` after line 25:

```python
@dataclass
class InlineError:
    """A single claim-level error with anchor text for injection."""
    quoted_text: str  # Exact substring from user's answer
    summary: str  # Brief label for <summary> tag
    feedback: str  # Natural prose feedback
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInlineErrorDataclass -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add InlineError dataclass for claim-level feedback"
```

---

## Task 2: Add InlineAnswerFeedback Dataclass

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInlineAnswerFeedback -v`
Expected: FAIL with "cannot import name 'InlineAnswerFeedback'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py`:

```python
@dataclass
class InlineAnswerFeedback:
    """Per-answer feedback with inline errors and optional writing note."""
    question_id: str
    label: str
    score: float
    errors: list[InlineError] = field(default_factory=list)
    writing_note: Optional[str] = None
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInlineAnswerFeedback -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add InlineAnswerFeedback dataclass"
```

---

## Task 3: Implement strip_feedback Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestStripFeedback -v`
Expected: FAIL with "cannot import name 'strip_feedback'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py`:

```python
def strip_feedback(content: str) -> str:
    """Remove all existing feedback annotations from quiz content.

    Removes:
    - All <details>...</details> blocks (inline annotations)
    - The ## Summary section at end of file

    Args:
        content: Raw quiz.md content

    Returns:
        Content with feedback stripped, ready for fresh annotations
    """
    # Remove all <details> blocks
    result = re.sub(r'<details>.*?</details>\n*', '', content, flags=re.DOTALL)

    # Remove ## Summary section at end of file
    result = re.sub(r'\n---\n\n## Summary.*', '', result, flags=re.DOTALL)

    return result
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestStripFeedback -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add strip_feedback function"
```

---

## Task 4: Implement inject_error Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInjectError -v`
Expected: FAIL with "cannot import name 'inject_error'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py`:

```python
def inject_error(content: str, error: "InlineError") -> str:
    """Inject a single error annotation after the quoted text.

    Args:
        content: The answer text to annotate
        error: InlineError with quoted_text anchor and feedback

    Returns:
        Content with <details> block inserted after quoted text,
        or unchanged if quoted text not found
    """
    if error.quoted_text not in content:
        return content  # Text not found, skip

    feedback_html = f'''
<details>
<summary>{error.summary}</summary>
{error.feedback}
</details>'''

    # Replace only first occurrence
    return content.replace(error.quoted_text, error.quoted_text + feedback_html, 1)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInjectError -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add inject_error function"
```

---

## Task 5: Implement inject_writing_note Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInjectWritingNote -v`
Expected: FAIL with "cannot import name 'inject_writing_note'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py`:

```python
def inject_writing_note(answer: str, writing_note: Optional[str]) -> str:
    """Append writing feedback at end of an answer.

    Args:
        answer: The answer text
        writing_note: Holistic writing feedback with rewrite example, or None

    Returns:
        Answer with writing note appended, or unchanged if no note
    """
    if not writing_note:
        return answer

    note_html = f'''
<details>
<summary>Writing</summary>
{writing_note}
</details>'''

    return answer.rstrip() + note_html + "\n"
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInjectWritingNote -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add inject_writing_note function"
```

---

## Task 6: Implement inject_inline_feedback Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInjectInlineFeedback -v`
Expected: FAIL with "cannot import name 'inject_inline_feedback'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py`:

```python
def inject_inline_feedback(content: str, feedbacks: list["InlineAnswerFeedback"]) -> str:
    """Inject inline feedback annotations into quiz content.

    For each answer:
    1. Inject error annotations after quoted text
    2. Append writing note at end of answer block

    Args:
        content: Raw quiz.md content
        feedbacks: List of InlineAnswerFeedback for each question

    Returns:
        Content with inline annotations injected
    """
    result = content

    for feedback in feedbacks:
        # Inject each error annotation
        for error in feedback.errors:
            result = inject_error(result, error)

        # Inject writing note - find answer section and append
        if feedback.writing_note:
            # Find pattern: **Answer:** ... until --- or ### or end
            # Insert writing note before the separator
            pattern = r'(\*\*Answer:\*\*.*?)(\n\n---|\n\n###|\Z)'

            def insert_note(match):
                answer_part = match.group(1)
                separator = match.group(2) if match.group(2) else ''
                note_block = f'''
<details>
<summary>Writing</summary>
{feedback.writing_note}
</details>
'''
                return answer_part + note_block + separator

            result = re.sub(pattern, insert_note, result, count=1, flags=re.DOTALL)

    return result
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInjectInlineFeedback -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add inject_inline_feedback function"
```

---

## Task 7: Implement format_summary_feedback Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestFormatSummaryFeedback -v`
Expected: FAIL with "cannot import name 'format_summary_feedback'"

**Step 3: Write minimal implementation**

Add to `tools/edps/evaluation.py`:

```python
def format_summary_feedback(feedback: QuizFeedback, assessment_date: str) -> str:
    """Format slimmed-down summary section for end of quiz file.

    Args:
        feedback: QuizFeedback with thematic insights and tutor's note
        assessment_date: Date string (YYYY-MM-DD)

    Returns:
        Markdown summary section with collapsible details
    """
    lines = [
        "",
        "---",
        "",
        "## Summary",
        "",
        f"**Score:** {feedback.total_score:.0f}/8 | **Assessed:** {assessment_date}",
        "",
    ]

    if feedback.thematic_insights:
        ti = feedback.thematic_insights
        wc = ti.writing_craft
        lines.extend([
            "<details>",
            "<summary>Thematic Insights</summary>",
            "",
            f"**Source Mastery:** {ti.source_mastery}",
            "",
            f"**Reasoning Quality:** {ti.reasoning_quality}",
            "",
            f"**Writing Craft:** Precision {wc.precision}/5 | Clarity {wc.clarity}/5 | Economy {wc.economy}/5",
            "",
            f"**Practice:** {wc.suggestion}",
            "</details>",
            "",
        ])

    if feedback.tutors_note:
        lines.extend([
            "<details>",
            "<summary>Tutor's Note</summary>",
            "",
            feedback.tutors_note,
            "</details>",
        ])

    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestFormatSummaryFeedback -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add format_summary_feedback function"
```

---

## Task 8: Update Prompt for Inline Schema

**Files:**
- Modify: `tools/edps/prompts/prompts.yaml`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInlinePromptSchema -v`
Expected: FAIL (prompt doesn't yet have new schema)

**Step 3: Update the prompt template**

Modify `tools/edps/prompts/prompts.yaml` - update the assessment prompt section to include the new inline schema with `errors[]`, `quoted_text`, and `writing_note` fields. The prompt should instruct the LLM to quote exact text from answers when identifying errors.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestInlinePromptSchema -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/prompts/prompts.yaml tests/test_evaluation.py
git commit -m "feat(feedback): update prompt for inline claim-level schema"
```

---

## Task 9: Add parse_inline_response Function

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
class TestParseInlineResponse:
    """Tests for parsing inline feedback responses."""

    def test_parses_errors_array(self):
        """Should parse errors[] with quoted_text and feedback."""
        from edps.evaluation import parse_inline_response

        response = '''{
  "recall": {"points": [], "one_sentence_ok": true, "one_sentence_note": "", "score": 4, "reasoning": ""},
  "quiz": {
    "answers": [
      {
        "question_id": "q1",
        "label": "Q1: Main Claim",
        "score": 0.5,
        "errors": [
          {
            "quoted_text": "Specialization leads to division",
            "summary": "Causal inversion",
            "feedback": "Exchange enables specialization."
          }
        ],
        "writing_note": "Lead with causes."
      }
    ],
    "total_score": 6,
    "thematic_insights": {
      "source_mastery": "Strong grasp.",
      "reasoning_quality": "Sound logic.",
      "writing_craft": {"precision": 4, "clarity": 4, "economy": 3, "suggestion": "Cut filler."}
    },
    "tutors_note": "Keep it up."
  }
}'''

        recall_fb, quiz_fb, inline_feedbacks = parse_inline_response(response)

        assert len(inline_feedbacks) == 1
        assert inline_feedbacks[0].question_id == "q1"
        assert len(inline_feedbacks[0].errors) == 1
        assert inline_feedbacks[0].errors[0].quoted_text == "Specialization leads to division"

    def test_handles_empty_errors(self):
        """Should handle answers with no errors."""
        from edps.evaluation import parse_inline_response

        response = '''{
  "recall": {"points": [], "one_sentence_ok": true, "one_sentence_note": "", "score": 5, "reasoning": ""},
  "quiz": {
    "answers": [{"question_id": "q1", "label": "Q1", "score": 1.0, "errors": [], "writing_note": null}],
    "total_score": 8,
    "thematic_insights": null,
    "tutors_note": null
  }
}'''

        recall_fb, quiz_fb, inline_feedbacks = parse_inline_response(response)

        assert len(inline_feedbacks[0].errors) == 0
        assert inline_feedbacks[0].writing_note is None
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py::TestParseInlineResponse -v`
Expected: FAIL

**Step 3: Implement parse_inline_response**

Add function that extracts JSON, parses the new schema with `errors[]` and `writing_note`, and returns `(RecallFeedback, QuizFeedback, list[InlineAnswerFeedback])`.

**Step 4: Run test to verify it passes**

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): add parse_inline_response for claim-level schema"
```

---

## Task 10: Update Main Assessment Function

**Files:**
- Modify: `tools/edps/evaluation.py` (the main orchestration function)
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
class TestAssessmentInline:
    """Tests for assessment with inline feedback."""

    def test_injects_inline_feedback(self, tmp_path):
        """Should inject inline feedback instead of appending at end."""
        from edps.evaluation import assess_section

        section = tmp_path / "sections" / "001"
        section.mkdir(parents=True)
        (section / "EDPS-test-001.txt").write_text("Source content.")
        (section / "recall.md").write_text("## From Memory\n\n1. Point\n\n## One Sentence\n\nSum")
        (section / "quiz.md").write_text('''### 1. Q1

**Answer:** Specialization leads to division of labor.

---
''')

        mock_response = # ... mock with inline schema

        with patch("edps.core.llm.LLMClient") as mock_client:
            # ... setup mock
            assess_section(section, "test", "001")

        quiz_content = (section / "quiz.md").read_text()

        assert "<details>" in quiz_content
        assert "## Summary" in quiz_content
```

**Step 2: Run test to verify it fails**

**Step 3: Update the main orchestration function**

Change flow from:
```python
quiz_md = format_quiz_feedback(...)
with open(quiz_path, "a") as f:
    f.write(quiz_md)
```

To:
```python
quiz_content = strip_feedback(quiz_raw)
quiz_content = inject_inline_feedback(quiz_content, inline_feedbacks)
summary_md = format_summary_feedback(quiz_feedback, date)
quiz_content = quiz_content.rstrip() + summary_md
quiz_path.write_text(quiz_content)
```

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add tools/edps/evaluation.py tests/test_evaluation.py
git commit -m "feat(feedback): update main function for inline flow"
```

---

## Task 11: Add Fuzzy Matching Fallback

**Files:**
- Modify: `tools/edps/evaluation.py`
- Test: `tests/test_evaluation.py`

**Step 1: Write the failing test**

```python
class TestFuzzyMatching:
    """Tests for fuzzy matching fallback."""

    def test_fuzzy_matches_similar_text(self):
        """Should find close match when exact text differs slightly."""
        from edps.evaluation import find_best_match

        content = "Division of labor results from the propensity to exchange."
        quoted = "Division of labor results from propensity to exchange"  # Missing "the"

        match = find_best_match(content, quoted, threshold=0.8)
        assert match is not None

    def test_returns_none_below_threshold(self):
        """Should return None if no match above threshold."""
        from edps.evaluation import find_best_match

        content = "Completely different text here."
        quoted = "Division of labor results from exchange."

        match = find_best_match(content, quoted, threshold=0.8)
        assert match is None
```

**Step 2: Run test to verify it fails**

**Step 3: Implement find_best_match using difflib.SequenceMatcher**

**Step 4: Update inject_error to use fuzzy matching as fallback**

**Step 5: Run tests and commit**

```bash
git commit -m "feat(feedback): add fuzzy matching fallback"
```

---

## Task 12: Run Full Test Suite

**Step 1: Run all tests**

```bash
PYTHONPATH="$PWD/tools" python -m pytest tests/test_evaluation.py -v
```

**Step 2: Fix any regressions**

**Step 3: Commit fixes**

```bash
git commit -m "fix(feedback): ensure backward compatibility"
```

---

## Task 13: Manual Integration Test

**Step 1: Run on real quiz**

```bash
PYTHONPATH="$PWD/tools" python -m edps.cli assess wealth-of-nations 002
```

**Step 2: Verify in Obsidian**

- Collapsible sections work
- Inline annotations appear after errors
- Summary at end is collapsible

**Step 3: Commit any adjustments**

---

## Success Criteria

- [ ] InlineError and InlineAnswerFeedback dataclasses created
- [ ] strip_feedback removes old annotations and summary
- [ ] inject_error inserts after exact/fuzzy matched text
- [ ] inject_writing_note appends at answer end
- [ ] inject_inline_feedback orchestrates injection
- [ ] format_summary_feedback creates collapsible summary
- [ ] Prompt updated for inline schema
- [ ] parse_inline_response handles new schema
- [ ] Main function uses new flow
- [ ] Fuzzy matching fallback works
- [ ] All tests pass
- [ ] Manual test confirms Obsidian rendering
