# AI Evaluation Design

> Created: 2025-12-25
> Status: Approved

## Overview

Add AI-powered evaluation of recall and quiz answers to replace self-scoring. The AI evaluates answers against the original source text, provides adaptive feedback, and updates progress.yaml with objective scores.

## User Flow

```
1. User fills out recall.md and quiz.md for a section
2. User commits: git add ... && git commit -m "Complete section 001"
3. Pre-commit hook detects homework files
4. AI evaluation runs (~15 sec)
5. Feedback appended to recall.md and quiz.md
6. progress.yaml updated with AI scores
7. Modified files auto-staged
8. Commit proceeds
```

For non-homework commits (code, docs, features), the hook exits immediately with no delay.

## Command

```bash
# Manual evaluation (also available)
edps eval <book-slug> <section-id>

# Example
edps eval wealth-of-nations 001
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | Both recall + quiz together | Single evaluation, single output |
| Source | Original text (.txt in section) | More authoritative than AI summary |
| Output | Append to existing files | Everything in one place per artifact |
| Strictness | Generous | Credit for directionally correct; focus on learning |
| Feedback format | Adaptive | Concise for correct, detailed for missed |
| Scores | Replace self-scores | AI becomes source of truth |
| Trigger | Pre-commit hook | Automatic, no manual step |

## Input Files

Per section, the evaluator reads:

```
books/<slug>/sections/<id>/
├── EDPS-<slug>-<id>.txt    # Source text (ground truth)
├── recall.md                # User's recall notes
└── quiz.md                  # User's quiz answers
```

## Output Format

### Recall Feedback

Appended to `recall.md`:

```markdown
---

## AI Feedback

> Evaluated: 2025-12-25
> Source: EDPS-wealth-of-nations-001.txt

### From Memory Assessment

| Point | Score | Note |
|-------|-------|------|
| 1. Division of labor critical to wealth | ✓ | Correct |
| 2. Three causes of productivity | ✓ | Correct |
| 3. Pin factory example | ✓ | Accurate |
| 4. Modern parallel | ✓ | Good application |
| 5. Agriculture limitation | ⚠️ | Partially correct — see below |

**Point 5 detail:** Smith's argument focuses on *seasonal constraints* forcing farmers to switch tasks, not limitations of nature generally.

### One Sentence Assessment

✓ Strong — captures the core mechanism and societal impact.

### AI Score: 4 / 5

**Reasoning:** Excellent recall of main claims and mechanisms. Minor imprecision on agriculture argument.
```

### Quiz Feedback

Appended to `quiz.md`:

```markdown
---

## AI Feedback

> Evaluated: 2025-12-25
> Source: EDPS-wealth-of-nations-001.txt

### Recall Questions (1-5)

| Q | Score | Feedback |
|---|-------|----------|
| 1 | ✓ 1/1 | Correct |
| 2 | ✓ 1/1 | Correct |
| 3 | ⚠️ 0.5/1 | Close — actual is 48,000 total, not 4,800 |
| 4 | ✓ 1/1 | Correct |
| 5 | ✓ 1/1 | Excellent explanation |

### Explain Questions (6-7)

| Q | Score | Feedback |
|---|-------|----------|
| 6 | ✓ 1/1 | Correct |
| 7 | ✓ 1/1 | Correct |

### Apply Question (8)

| Q | Score | Feedback |
|---|-------|----------|
| 8 | ✓ 1/1 | Thoughtful connection |

**Q3 detail:** Smith states ten workers produce "upwards of forty-eight thousand pins in a day" — the per-worker rate (4,800) is correct, but the question asked for total output.

### AI Score: 7.5 / 8

**Reasoning:** Strong comprehension throughout. One minor numerical error.
```

## Progress Integration

After evaluation, `progress.yaml` updates:

```yaml
completed_sections:
  - "001"

quiz_scores:
  "001": 7.5    # AI-evaluated

recall_scores:
  "001": 4      # AI-evaluated
```

## Pre-commit Hook Logic

```python
# Pseudocode for extended hook

def pre_commit_hook(staged_files):
    # Parse staged files for homework
    homework = parse_homework_files(staged_files)

    if not homework:
        return  # Exit fast for non-homework commits

    for book_slug, sections in homework.items():
        for section_id in sections:
            section_path = f"books/{book_slug}/sections/{section_id}"

            # Check if section is filled (existing logic)
            status = check_section_completion(section_path)

            if status.is_complete:
                # NEW: Run AI evaluation
                evaluate_section(book_slug, section_id)

    # Update progress.yaml (existing logic, now with AI scores)
    update_progress(...)
```

## Evaluation Rubric

### Recall (0-5 scale)

| Score | Meaning |
|-------|---------|
| 5 | Near-perfect recall of main claims, mechanisms, and examples |
| 4 | Accurate main claims, minor details missed |
| 3 | Core argument captured, significant details missing |
| 2 | General topic understood, argument structure unclear |
| 1 | Vague impressions only |
| 0 | No meaningful recall |

### Quiz (per question)

- **Recall questions (1-5):** 1 point each, partial credit 0.5 for close answers
- **Explain questions (6-7):** 1 point each, must demonstrate understanding
- **Apply question (8):** 1 point, must connect to source material

### Generous Evaluation Principles

1. Credit directionally correct answers even if wording differs
2. Accept modern examples and applications not in source
3. Partial credit for incomplete but accurate answers
4. Focus feedback on learning, not punishment

## API Considerations

- Model: Claude (via existing Azure integration)
- Estimated tokens per evaluation: ~4,000 input, ~1,000 output
- Estimated latency: 10-20 seconds
- Cost: ~$0.02-0.05 per section evaluation

## Error Handling

| Scenario | Behavior |
|----------|----------|
| API timeout | Log warning, commit proceeds without eval, section marked for retry |
| API error | Log error, commit proceeds, no scores updated |
| Partial eval | Save whatever feedback completed, note incomplete |
| Already evaluated | Skip (check for existing `## AI Feedback` section) |

## Future Enhancements

- GitHub Actions alternative for async evaluation (Issue #1)
- Batch evaluation: `edps eval --all`
- Re-evaluation: `edps eval --force` to overwrite existing feedback
- Comparison mode: Show AI score vs self-score trends over time

## Implementation Tasks

1. Create `tools/edps/evaluation.py` with evaluation logic
2. Create evaluation prompt template
3. Add `edps eval` CLI command
4. Extend pre-commit hook to call evaluation
5. Update progress.yaml schema for AI scores
6. Add tests for evaluation parsing and scoring
