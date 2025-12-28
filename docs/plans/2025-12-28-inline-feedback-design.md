# Inline Claim-Level Feedback Design

**Date:** 2025-12-28
**Status:** Design approved, pending implementation
**Extends:** 2025-12-27-evaluation-quiz-redesign.md

---

## Problem Statement

Current evaluation appends all AI feedback at the end of quiz.md. This forces the reader to scroll back and forth between their answer and the corresponding feedback—especially painful for longer answers with multiple claims.

**Current flow:**
```
Question → Your Answer → Question → Your Answer → ... → [scroll down] → AI Feedback block
```

**Desired flow:**
```
Question → Your Answer (with inline annotations on errors) → Question → ...
```

---

## Design Goals

1. **Feedback adjacent to errors** — Annotations appear right after the problematic text
2. **Minimal visual clutter** — Use collapsible sections; only errors annotated
3. **Clean re-evaluation** — Old feedback replaced, not accumulated
4. **Preserve holistic insights** — Summary section remains at end (slimmed down)

---

## Feedback Format

### Inline Error Annotations

Collapsible `<details>` blocks inserted after the exact quoted text containing an error:

```markdown
**Answer:** Division of labor results from innate need to truck, exchange, and barter.
Specialization leads to division of labor resulting in increased productivity.
<details>
<summary>Causal inversion</summary>
Exchange certainty enables specialization, not the reverse. Smith's chain: exchange -> specialization -> surplus.
</details>
Without exchange, there's no motivation to produce excess.
```

**Characteristics:**
- Summary line is brief label (e.g., "Causal inversion")
- Body contains natural prose covering accuracy and reasoning implicitly
- Only errors annotated; correct claims left unmarked

### Writing Feedback

One collapsible block at the end of each answer (not per-claim). Includes a rewritten example:

```markdown
...last sentence of answer.

<details>
<summary>Writing</summary>
Lead with causes before effects. Example: "The certainty of exchange motivates specialization, which increases productivity and creates surplus for trade."
</details>

---
```

**Characteristics:**
- Holistic feedback on prose quality for the entire answer
- Includes concrete rewrite example showing improvement
- Omitted if writing is fine

### Summary Section (End of File)

Slimmed-down summary with collapsible sections:

```markdown
---

## Summary

**Score:** 6/8 | **Evaluated:** 2025-12-28

<details>
<summary>Thematic Insights</summary>
Source mastery: Consistently grasps the core argument...
Reasoning quality: Good use of counterfactuals...
</details>

<details>
<summary>Tutor's Note</summary>
You demonstrate strong understanding of Smith's core thesis...
</details>
```

---

## LLM Response Schema

```json
{
  "quiz": {
    "answers": [
      {
        "question_id": "q1",
        "label": "Q1: Main Claim",
        "score": 0.5,
        "errors": [
          {
            "quoted_text": "Specialization leads to division of labor",
            "summary": "Causal inversion",
            "feedback": "Exchange certainty enables specialization, not the reverse. Smith's chain: exchange -> specialization -> surplus."
          }
        ],
        "writing_note": "Lead with causes before effects. Example: \"The certainty of exchange motivates specialization, which increases productivity and creates surplus for trade.\""
      }
    ],
    "total_score": 6,
    "thematic_insights": {
      "source_mastery": "...",
      "reasoning_quality": "...",
      "writing_craft": {
        "precision": 4,
        "clarity": 4,
        "economy": 4,
        "suggestion": "..."
      }
    },
    "tutors_note": "..."
  }
}
```

**Key fields:**
- `errors[]` — Array of claim-level errors (empty if answer fully correct)
- `quoted_text` — Exact substring from user's answer (used for injection location)
- `summary` — Brief label for the `<summary>` tag
- `feedback` — Natural prose covering accuracy and reasoning
- `writing_note` — Holistic writing feedback with rewrite example (null if not needed)

---

## Injection Logic

### Step 1: Strip Old Feedback

Remove all existing `<details>...</details>` blocks before re-evaluation:

```python
def strip_feedback(content: str) -> str:
    """Remove all <details>...</details> blocks."""
    return re.sub(r'<details>.*?</details>\n*', '', content, flags=re.DOTALL)
```

### Step 2: Locate Answer Blocks

Parse quiz.md to find each answer. Pattern matches from `**Answer:**` to `---` or next `###`:

```python
ANSWER_PATTERN = r'(\*\*Answer:\*\*\s*)(.+?)(\n\n---|\n\n###|\Z)'
```

### Step 3: Inject Error Annotations

For each error, find the quoted text and insert feedback after it:

```python
def inject_error(content: str, error: dict) -> str:
    quoted = error["quoted_text"]
    feedback_html = f'''<details>
<summary>{error["summary"]}</summary>
{error["feedback"]}
</details>
'''
    # Insert after the quoted text
    return content.replace(quoted, quoted + "\n" + feedback_html, 1)
```

### Step 4: Inject Writing Note

Find the answer's ending and insert writing note just before:

```python
def inject_writing_note(answer_text: str, writing_note: str) -> str:
    if not writing_note:
        return answer_text
    note_html = f'''
<details>
<summary>Writing</summary>
{writing_note}
</details>
'''
    # Insert before the trailing newlines/separator
    return answer_text.rstrip() + "\n" + note_html + "\n"
```

### Step 5: Append Summary

Add slimmed-down summary section at end of file.

### Edge Cases

| Case | Handling |
|------|----------|
| Quoted text not found exactly | Fuzzy match (80% similarity threshold) or skip with warning |
| Multiple identical phrases | Annotate first occurrence only |
| Empty errors array | No inline annotations; writing note only (if any) |
| No errors and no writing note | Answer left unchanged |

---

## Implementation Changes

### Files to Modify

| File | Changes |
|------|---------|
| `tools/edps/evaluation.py` | New functions: `strip_feedback()`, `inject_inline_feedback()`, `format_summary_feedback()`. Modify `evaluate_section()` flow. |
| `tools/edps/prompts/prompts.yaml` | Update evaluation prompt to request new schema with `errors[]`, `quoted_text`, `writing_note` |

### Function Changes in `evaluation.py`

| Function | Change |
|----------|--------|
| `build_evaluation_prompt()` | Update prompt to request new schema |
| `parse_evaluation_response()` | Parse `errors[]` and `writing_note` fields |
| `format_quiz_feedback()` | Replace with `inject_inline_feedback()` |
| New: `strip_feedback()` | Remove existing `<details>` blocks |
| New: `format_summary_feedback()` | Generate slimmed-down summary |

### Flow Change in `evaluate_section()`

```python
# Current:
quiz_md = format_quiz_feedback(...)
with open(quiz_path, "a") as f:
    f.write(quiz_md)

# New:
quiz_content = strip_feedback(quiz_raw)
quiz_content = inject_inline_feedback(quiz_content, quiz_feedback)
quiz_content = append_summary(quiz_content, quiz_feedback, eval_date, source_file)
quiz_path.write_text(quiz_content)
```

---

## Success Criteria

- [ ] Error feedback appears inline after the specific problematic text
- [ ] Feedback uses collapsible `<details>` sections
- [ ] Writing feedback appears at end of answer with rewrite example
- [ ] Summary section at end of file is collapsible and concise
- [ ] Re-evaluation replaces old feedback cleanly
- [ ] Correct claims have no annotations
- [ ] Works in Obsidian preview and GitHub rendering
