# Design: Auto-Progress Sync via Git Hook

**Date:** 2025-12-23
**Status:** Approved

---

## Problem

Users must manually update `progress.yaml` after completing section homework. This is tedious and error-prone. The system should detect completion automatically.

## Solution

A git pre-commit hook that:
1. Detects which sections have staged changes
2. Checks if homework files meet completion criteria
3. Updates `progress.yaml` with completion status and extracted scores
4. Auto-stages the updated progress file

---

## Completion Criteria

### Recall (`recall.md`)

A recall file is complete when:
- No `[Your answer]` placeholders remain in the text
- Score line matches pattern: `**My score**: [X] / 5` where X is 0-5

### Quiz (`quiz.md`)

A quiz file is complete when:
- All `**Answer:**` sections have non-whitespace text following them
- Total line matches pattern: `**Total: X / 8**` where X is a number

### Section

A section is complete when BOTH recall AND quiz pass their checks.

---

## Data Flow

```
git commit
    │
    ▼
Pre-commit hook triggers
    │
    ▼
Parse staged files: git diff --cached --name-only
    │
    ▼
Filter for: books/*/sections/*/recall.md or quiz.md
    │
    ▼
Extract (book-slug, section-id) pairs from paths
    │
    ▼
For each affected section:
    ├── Read recall.md → check completion, extract score
    ├── Read quiz.md → check completion, extract score
    └── Determine if section is complete
    │
    ▼
Update progress.yaml for affected book(s):
    ├── completed_sections: add/remove section ID
    ├── quiz_scores: set extracted score
    ├── recall_scores: set extracted score
    └── stats: recalculate averages
    │
    ▼
Auto-stage progress.yaml
    │
    ▼
Commit proceeds
```

---

## Path Parsing

Relevant paths match:
```
books/{book-slug}/sections/{section-id}/recall.md
books/{book-slug}/sections/{section-id}/quiz.md
```

Regex: `^books/([^/]+)/sections/([^/]+)/(recall|quiz)\.md$`

---

## Progress.yaml Updates

### Fields Updated

| Field | Source | Calculation |
|-------|--------|-------------|
| `completed_sections` | Detection logic | List of section IDs where both recall + quiz complete |
| `quiz_scores` | `**Total: X / 8**` | Extracted integer X |
| `recall_scores` | `**My score**: [X] / 5` | Extracted integer X |
| `stats.total_sections_completed` | Derived | `len(completed_sections)` |
| `stats.average_quiz_score` | Derived | `mean(quiz_scores.values())` or null |
| `stats.average_recall_score` | Derived | `mean(recall_scores.values())` or null |

### Authoritative Behavior

The hook is authoritative for affected sections:
- If a section was previously marked complete but files no longer pass checks, it is removed from `completed_sections`
- Scores are always recalculated from files, not trusted from existing YAML
- Only affected sections are rechecked; unaffected sections remain unchanged

---

## Implementation Structure

### New Files

```
tools/
├── edps/
│   ├── progress.py      # Core detection and update logic
│   └── cli.py           # Add 'sync' and 'init-hooks' commands
└── hooks/
    └── pre-commit       # Shell script that invokes Python
```

### Module: `edps/progress.py`

```python
# Public API

def check_recall_completion(recall_path: Path) -> tuple[bool, int | None]:
    """Check if recall.md is complete. Returns (is_complete, score)."""

def check_quiz_completion(quiz_path: Path) -> tuple[bool, int | None]:
    """Check if quiz.md is complete. Returns (is_complete, score)."""

def check_section_completion(section_path: Path) -> SectionStatus:
    """Check if a section is complete. Returns status with scores."""

def parse_staged_files(staged_files: list[str]) -> dict[str, set[str]]:
    """Parse staged file paths. Returns {book_slug: {section_ids}}."""

def update_progress(book_slug: str, section_updates: dict) -> None:
    """Update progress.yaml for a book with new section statuses."""

def recalculate_stats(progress: dict) -> dict:
    """Recalculate derived stats from scores."""

def run_hook(staged_files: list[str]) -> list[Path]:
    """Main hook entry point. Returns list of modified progress files."""
```

### Hook Script: `hooks/pre-commit`

```bash
#!/bin/bash
set -e

# Get staged files
STAGED=$(git diff --cached --name-only)

# Run progress sync
MODIFIED=$(python -m edps.progress --hook --staged-files "$STAGED")

# Auto-stage any modified progress files
if [ -n "$MODIFIED" ]; then
    echo "$MODIFIED" | xargs git add
fi
```

### CLI Commands

```bash
# Install the pre-commit hook
edps init-hooks

# Manual sync (without committing)
edps sync wealth-of-nations          # Sync one book (affected sections only)
edps sync wealth-of-nations --full   # Full rescan of all sections
edps sync --all                      # Full rescan of all books
```

---

## Edge Cases

### No homework files exist

If `recall.md` or `quiz.md` doesn't exist in a section folder, that section cannot be complete. Skip silently.

### Partial completion

If recall is complete but quiz is not (or vice versa), section is NOT complete. Individual scores are still tracked if extractable.

### Malformed score lines

If score lines exist but don't match expected patterns, treat as incomplete. Log a warning but don't fail the commit.

### Multiple books in one commit

Handle independently. Each book's `progress.yaml` is updated separately.

### progress.yaml doesn't exist

Create it with default structure if missing.

---

## Testing Strategy

### Unit Tests

1. **Recall detection**
   - Template file (placeholders) → incomplete
   - Filled file with score → complete, score extracted
   - Filled file without score → incomplete
   - Partial fill (some placeholders remain) → incomplete

2. **Quiz detection**
   - Template file (empty answers) → incomplete
   - All answers filled with total → complete, score extracted
   - Some answers filled → incomplete
   - Answers filled but no total → incomplete

3. **Path parsing**
   - Valid paths extracted correctly
   - Non-matching paths filtered out
   - Multiple books/sections parsed

4. **Stats calculation**
   - Empty scores → null averages
   - Single score → that value
   - Multiple scores → correct mean

### Integration Tests

1. **Hook simulation**
   - Stage recall + quiz for section → progress.yaml updated
   - Stage incomplete files → no change to completed_sections
   - Stage files for multiple sections → all updated

2. **Authoritative behavior**
   - Pre-mark section complete, then stage incomplete files → removed from completed_sections

### Fixtures

Create test fixtures in `tests/fixtures/`:
- `recall_template.md` - unfilled template
- `recall_complete.md` - properly filled
- `recall_partial.md` - partially filled
- `quiz_template.md` - unfilled template
- `quiz_complete.md` - properly filled
- `quiz_no_total.md` - answers but no score

---

## Non-Goals

- Tracking weekly synthesis completion (future enhancement)
- Tracking book-level outputs completion (future enhancement)
- Streak calculation (requires date tracking, out of scope)
- Time spent tracking (no reliable way to detect)
