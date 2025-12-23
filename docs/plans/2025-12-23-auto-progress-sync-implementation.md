# Auto-Progress Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automate progress.yaml updates via a git pre-commit hook that detects completed sections and extracts scores.

**Architecture:** A new `progress.py` module handles detection logic. Two CLI commands (`sync`, `init-hooks`) provide manual access. A bash pre-commit hook invokes the Python module on staged files.

**Tech Stack:** Python 3.11+, typer, pyyaml, pytest, regex

---

## Task 1: Create Test Fixtures

**Files:**
- Create: `tests/fixtures/recall_template.md`
- Create: `tests/fixtures/recall_complete.md`
- Create: `tests/fixtures/recall_partial.md`
- Create: `tests/fixtures/quiz_template.md`
- Create: `tests/fixtures/quiz_complete.md`
- Create: `tests/fixtures/quiz_partial.md`

**Step 1: Create fixtures directory**

```bash
mkdir -p tests/fixtures
```

**Step 2: Create recall_template.md (unfilled)**

```markdown
# Recall: Section [ID]

> Generator: Reader-written
> Date: [YYYY-MM-DD]
> Time spent: [X] minutes

---

## From Memory

### 1. Main Claim
[Your answer]

### 2. Key Mechanism
[Your answer]

### 3. Example I Remember
[Your answer]

---

## Self-Assessment

**My score**: [ ] / 5
```

**Step 3: Create recall_complete.md (properly filled)**

```markdown
# Recall: Section 001

> Generator: Reader-written
> Date: 2025-12-22
> Time spent: 15 minutes

---

## From Memory

### 1. Main Claim
Division of labor increases productivity through specialization.

### 2. Key Mechanism
Workers become more dexterous, save time switching tasks, and invent better tools.

### 3. Example I Remember
Pin factory example - 10 workers produce 48,000 pins vs 10-20 individually.

---

## Self-Assessment

**My score**: [4] / 5
```

**Step 4: Create recall_partial.md (some placeholders remain)**

```markdown
# Recall: Section 002

> Generator: Reader-written
> Date: 2025-12-22
> Time spent: 10 minutes

---

## From Memory

### 1. Main Claim
Trade arises from the human propensity to barter.

### 2. Key Mechanism
[Your answer]

### 3. Example I Remember
The butcher and baker example.

---

## Self-Assessment

**My score**: [3] / 5
```

**Step 5: Create quiz_template.md (unfilled)**

```markdown
# Quiz: Section [ID]

> Total questions: 8

---

## Recall Questions

### 1. Main Claim
What was the central argument?

**Answer:**


---

### 2. Mechanism
What process did the author describe?

**Answer:**


---

## Score

- Recall (1-5): __ / 5
- Explain (6-7): __ / 2
- Apply (8): __ / 1
- **Total: __ / 8**
```

**Step 6: Create quiz_complete.md (properly filled)**

```markdown
# Quiz: Section 001

> Total questions: 8

---

## Recall Questions

### 1. Main Claim
What was the central argument?

**Answer:**
The division of labor is the primary cause of improvements in productive power.

---

### 2. Mechanism
What process did the author describe?

**Answer:**
Specialization leads to increased dexterity, time savings, and invention of machinery.

---

## Score

- Recall (1-5): 4 / 5
- Explain (6-7): 2 / 2
- Apply (8): 1 / 1
- **Total: 7 / 8**
```

**Step 7: Create quiz_partial.md (answers but no total)**

```markdown
# Quiz: Section 002

> Total questions: 8

---

## Recall Questions

### 1. Main Claim
What was the central argument?

**Answer:**
Trade is natural to humans.

---

### 2. Mechanism
What process did the author describe?

**Answer:**


---

## Score

- Recall (1-5): __ / 5
- Explain (6-7): __ / 2
- Apply (8): __ / 1
- **Total: __ / 8**
```

**Step 8: Commit fixtures**

```bash
git add tests/fixtures/
git commit -m "test: add fixtures for progress detection tests"
```

---

## Task 2: Recall Detection - Test and Implementation

**Files:**
- Create: `tests/test_progress.py`
- Create: `tools/edps/progress.py`

**Step 1: Write failing test for recall detection**

```python
# tests/test_progress.py
"""Tests for progress detection module."""
from pathlib import Path

import pytest

from edps.progress import check_recall_completion


FIXTURES = Path(__file__).parent / "fixtures"


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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestCheckRecallCompletion -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'edps.progress'"

**Step 3: Create progress.py with RecallResult and check_recall_completion**

```python
# tools/edps/progress.py
"""Progress detection and sync module."""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RecallResult:
    """Result of checking recall completion."""
    is_complete: bool
    score: Optional[int]


def check_recall_completion(recall_path: Path) -> RecallResult:
    """
    Check if a recall.md file is complete.

    Complete when:
    - No [Your answer] placeholders remain
    - Score line matches: **My score**: [X] / 5

    Returns RecallResult with completion status and extracted score.
    """
    if not recall_path.exists():
        return RecallResult(is_complete=False, score=None)

    text = recall_path.read_text(encoding="utf-8")

    # Check for remaining placeholders
    has_placeholders = "[Your answer]" in text

    # Extract score: **My score**: [X] / 5
    score_pattern = r"\*\*My score\*\*:\s*\[(\d+)\]\s*/\s*5"
    score_match = re.search(score_pattern, text)

    score = int(score_match.group(1)) if score_match else None

    # Complete only if no placeholders AND score is present
    is_complete = not has_placeholders and score is not None

    return RecallResult(is_complete=is_complete, score=score)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestCheckRecallCompletion -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add tests/test_progress.py tools/edps/progress.py
git commit -m "feat: add recall completion detection with tests"
```

---

## Task 3: Quiz Detection - Test and Implementation

**Files:**
- Modify: `tests/test_progress.py`
- Modify: `tools/edps/progress.py`

**Step 1: Write failing test for quiz detection**

Add to `tests/test_progress.py`:

```python
from edps.progress import check_quiz_completion, QuizResult


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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestCheckQuizCompletion -v`

Expected: FAIL with "cannot import name 'check_quiz_completion'"

**Step 3: Add QuizResult and check_quiz_completion to progress.py**

Add to `tools/edps/progress.py`:

```python
@dataclass
class QuizResult:
    """Result of checking quiz completion."""
    is_complete: bool
    score: Optional[int]


def check_quiz_completion(quiz_path: Path) -> QuizResult:
    """
    Check if a quiz.md file is complete.

    Complete when:
    - All **Answer:** sections have non-whitespace text
    - Total line matches: **Total: X / 8**

    Returns QuizResult with completion status and extracted score.
    """
    if not quiz_path.exists():
        return QuizResult(is_complete=False, score=None)

    text = quiz_path.read_text(encoding="utf-8")

    # Find all **Answer:** sections and check they have content
    # Pattern: **Answer:** followed by content until next --- or ### or ## or end
    answer_pattern = r"\*\*Answer:\*\*\s*\n\s*\n"
    empty_answers = re.findall(answer_pattern, text)
    has_empty_answers = len(empty_answers) > 0

    # Also check for answers that are just whitespace before the next section
    # Split by **Answer:** and check each following section
    parts = re.split(r"\*\*Answer:\*\*", text)
    all_answers_filled = True
    for part in parts[1:]:  # Skip content before first Answer
        # Get content before next section marker
        content_match = re.match(r"(.*?)(?=\n---|\n###|\n##|\Z)", part, re.DOTALL)
        if content_match:
            answer_content = content_match.group(1).strip()
            if not answer_content:
                all_answers_filled = False
                break

    # Extract total score: **Total: X / 8**
    total_pattern = r"\*\*Total:\s*(\d+)\s*/\s*8\*\*"
    total_match = re.search(total_pattern, text)

    score = int(total_match.group(1)) if total_match else None

    # Complete only if all answers filled AND total score present
    is_complete = all_answers_filled and score is not None

    return QuizResult(is_complete=is_complete, score=score)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestCheckQuizCompletion -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add tests/test_progress.py tools/edps/progress.py
git commit -m "feat: add quiz completion detection with tests"
```

---

## Task 4: Section Detection - Test and Implementation

**Files:**
- Modify: `tests/test_progress.py`
- Modify: `tools/edps/progress.py`

**Step 1: Create test fixture directory structure**

```bash
mkdir -p tests/fixtures/sections/complete
mkdir -p tests/fixtures/sections/incomplete
```

Copy `recall_complete.md` and `quiz_complete.md` to `tests/fixtures/sections/complete/`
Copy `recall_complete.md` and `quiz_partial.md` to `tests/fixtures/sections/incomplete/`

```bash
cp tests/fixtures/recall_complete.md tests/fixtures/sections/complete/recall.md
cp tests/fixtures/quiz_complete.md tests/fixtures/sections/complete/quiz.md
cp tests/fixtures/recall_complete.md tests/fixtures/sections/incomplete/recall.md
cp tests/fixtures/quiz_partial.md tests/fixtures/sections/incomplete/quiz.md
```

**Step 2: Write failing test for section detection**

Add to `tests/test_progress.py`:

```python
from edps.progress import check_section_completion, SectionStatus


SECTIONS_FIXTURES = FIXTURES / "sections"


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
```

**Step 3: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestCheckSectionCompletion -v`

Expected: FAIL with "cannot import name 'check_section_completion'"

**Step 4: Add SectionStatus and check_section_completion to progress.py**

Add to `tools/edps/progress.py`:

```python
@dataclass
class SectionStatus:
    """Result of checking section completion."""
    is_complete: bool
    recall_score: Optional[int]
    quiz_score: Optional[int]


def check_section_completion(section_path: Path) -> SectionStatus:
    """
    Check if a section is complete.

    A section is complete when BOTH recall.md and quiz.md pass their checks.

    Returns SectionStatus with completion status and both scores.
    """
    recall_path = section_path / "recall.md"
    quiz_path = section_path / "quiz.md"

    recall_result = check_recall_completion(recall_path)
    quiz_result = check_quiz_completion(quiz_path)

    is_complete = recall_result.is_complete and quiz_result.is_complete

    return SectionStatus(
        is_complete=is_complete,
        recall_score=recall_result.score,
        quiz_score=quiz_result.score,
    )
```

**Step 5: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestCheckSectionCompletion -v`

Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add tests/ tools/edps/progress.py
git commit -m "feat: add section completion detection with tests"
```

---

## Task 5: Path Parsing - Test and Implementation

**Files:**
- Modify: `tests/test_progress.py`
- Modify: `tools/edps/progress.py`

**Step 1: Write failing test for path parsing**

Add to `tests/test_progress.py`:

```python
from edps.progress import parse_staged_files


class TestParseStagedFiles:
    """Tests for parse_staged_files function."""

    def test_parses_recall_and_quiz_paths(self):
        """Should extract book and section from valid paths."""
        staged = [
            "books/wealth-of-nations/sections/005/recall.md",
            "books/wealth-of-nations/sections/005/quiz.md",
        ]
        result = parse_staged_files(staged)
        assert result == {"wealth-of-nations": {"005"}}

    def test_handles_multiple_sections(self):
        """Should group multiple sections by book."""
        staged = [
            "books/wealth-of-nations/sections/001/recall.md",
            "books/wealth-of-nations/sections/002/quiz.md",
            "books/capital-vol-1/sections/003/recall.md",
        ]
        result = parse_staged_files(staged)
        assert result == {
            "wealth-of-nations": {"001", "002"},
            "capital-vol-1": {"003"},
        }

    def test_ignores_non_homework_files(self):
        """Should ignore files that aren't recall.md or quiz.md."""
        staged = [
            "books/wealth-of-nations/sections/001/summary.md",
            "books/wealth-of-nations/sections/001/podcast.md",
            "books/wealth-of-nations/progress.yaml",
            "README.md",
        ]
        result = parse_staged_files(staged)
        assert result == {}

    def test_handles_empty_list(self):
        """Should return empty dict for empty input."""
        result = parse_staged_files([])
        assert result == {}
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestParseStagedFiles -v`

Expected: FAIL with "cannot import name 'parse_staged_files'"

**Step 3: Add parse_staged_files to progress.py**

Add to `tools/edps/progress.py`:

```python
def parse_staged_files(staged_files: list[str]) -> dict[str, set[str]]:
    """
    Parse staged file paths to extract affected (book, section) pairs.

    Only considers files matching:
        books/{book-slug}/sections/{section-id}/recall.md
        books/{book-slug}/sections/{section-id}/quiz.md

    Returns dict mapping book_slug to set of section_ids.
    """
    pattern = re.compile(r"^books/([^/]+)/sections/([^/]+)/(recall|quiz)\.md$")

    result: dict[str, set[str]] = {}

    for path in staged_files:
        match = pattern.match(path)
        if match:
            book_slug = match.group(1)
            section_id = match.group(2)

            if book_slug not in result:
                result[book_slug] = set()
            result[book_slug].add(section_id)

    return result
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestParseStagedFiles -v`

Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add tests/test_progress.py tools/edps/progress.py
git commit -m "feat: add staged file path parsing with tests"
```

---

## Task 6: Progress Update - Test and Implementation

**Files:**
- Modify: `tests/test_progress.py`
- Modify: `tools/edps/progress.py`

**Step 1: Create progress.yaml test fixture**

Create `tests/fixtures/progress_initial.yaml`:

```yaml
completed_sections: []

quiz_scores: {}

recall_scores: {}

stats:
  total_sections_completed: 0
  average_quiz_score: null
  average_recall_score: null
```

**Step 2: Write failing test for progress update**

Add to `tests/test_progress.py`:

```python
import tempfile
import shutil
import yaml

from edps.progress import update_progress, SectionStatus


class TestUpdateProgress:
    """Tests for update_progress function."""

    def test_adds_completed_section(self, tmp_path):
        """Should add section to completed_sections and record scores."""
        # Setup: copy initial progress to temp dir
        progress_file = tmp_path / "progress.yaml"
        shutil.copy(FIXTURES / "progress_initial.yaml", progress_file)

        # Act: update with completed section
        updates = {
            "001": SectionStatus(is_complete=True, recall_score=4, quiz_score=7)
        }
        update_progress(tmp_path, updates)

        # Assert
        result = yaml.safe_load(progress_file.read_text())
        assert "001" in result["completed_sections"]
        assert result["quiz_scores"]["001"] == 7
        assert result["recall_scores"]["001"] == 4
        assert result["stats"]["total_sections_completed"] == 1
        assert result["stats"]["average_quiz_score"] == 7.0
        assert result["stats"]["average_recall_score"] == 4.0

    def test_removes_incomplete_section(self, tmp_path):
        """Should remove section from completed if it becomes incomplete."""
        # Setup: progress with section already complete
        progress_file = tmp_path / "progress.yaml"
        initial = {
            "completed_sections": ["001"],
            "quiz_scores": {"001": 7},
            "recall_scores": {"001": 4},
            "stats": {
                "total_sections_completed": 1,
                "average_quiz_score": 7.0,
                "average_recall_score": 4.0,
            },
        }
        progress_file.write_text(yaml.dump(initial))

        # Act: update with incomplete section
        updates = {
            "001": SectionStatus(is_complete=False, recall_score=4, quiz_score=None)
        }
        update_progress(tmp_path, updates)

        # Assert
        result = yaml.safe_load(progress_file.read_text())
        assert "001" not in result["completed_sections"]
        assert "001" not in result["quiz_scores"]
        assert "001" not in result["recall_scores"]
        assert result["stats"]["total_sections_completed"] == 0

    def test_preserves_unaffected_sections(self, tmp_path):
        """Should not modify sections not in updates."""
        # Setup: progress with existing section
        progress_file = tmp_path / "progress.yaml"
        initial = {
            "completed_sections": ["001"],
            "quiz_scores": {"001": 7},
            "recall_scores": {"001": 4},
            "stats": {
                "total_sections_completed": 1,
                "average_quiz_score": 7.0,
                "average_recall_score": 4.0,
            },
        }
        progress_file.write_text(yaml.dump(initial))

        # Act: update different section
        updates = {
            "002": SectionStatus(is_complete=True, recall_score=5, quiz_score=8)
        }
        update_progress(tmp_path, updates)

        # Assert: 001 unchanged, 002 added
        result = yaml.safe_load(progress_file.read_text())
        assert "001" in result["completed_sections"]
        assert "002" in result["completed_sections"]
        assert result["quiz_scores"]["001"] == 7
        assert result["quiz_scores"]["002"] == 8
        assert result["stats"]["total_sections_completed"] == 2
```

**Step 3: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestUpdateProgress -v`

Expected: FAIL with "cannot import name 'update_progress'"

**Step 4: Add update_progress to progress.py**

Add to `tools/edps/progress.py`:

```python
import yaml


def update_progress(book_path: Path, section_updates: dict[str, SectionStatus]) -> None:
    """
    Update progress.yaml for a book with new section statuses.

    - Adds/removes sections from completed_sections based on is_complete
    - Updates quiz_scores and recall_scores
    - Recalculates stats

    Args:
        book_path: Path to the book directory (contains progress.yaml)
        section_updates: Dict mapping section_id to SectionStatus
    """
    progress_file = book_path / "progress.yaml"

    # Load existing or create default
    if progress_file.exists():
        progress = yaml.safe_load(progress_file.read_text()) or {}
    else:
        progress = {}

    # Ensure required keys exist
    progress.setdefault("completed_sections", [])
    progress.setdefault("quiz_scores", {})
    progress.setdefault("recall_scores", {})
    progress.setdefault("stats", {})

    # Update each affected section
    for section_id, status in section_updates.items():
        if status.is_complete:
            # Add to completed if not already there
            if section_id not in progress["completed_sections"]:
                progress["completed_sections"].append(section_id)
            # Record scores
            if status.quiz_score is not None:
                progress["quiz_scores"][section_id] = status.quiz_score
            if status.recall_score is not None:
                progress["recall_scores"][section_id] = status.recall_score
        else:
            # Remove from completed
            if section_id in progress["completed_sections"]:
                progress["completed_sections"].remove(section_id)
            # Remove scores
            progress["quiz_scores"].pop(section_id, None)
            progress["recall_scores"].pop(section_id, None)

    # Sort completed_sections for consistency
    progress["completed_sections"] = sorted(progress["completed_sections"])

    # Recalculate stats
    progress["stats"] = _calculate_stats(progress)

    # Write back
    with open(progress_file, "w") as f:
        yaml.dump(progress, f, default_flow_style=False, sort_keys=False)


def _calculate_stats(progress: dict) -> dict:
    """Calculate derived stats from progress data."""
    completed = progress.get("completed_sections", [])
    quiz_scores = progress.get("quiz_scores", {})
    recall_scores = progress.get("recall_scores", {})

    stats = {
        "total_sections_completed": len(completed),
        "average_quiz_score": None,
        "average_recall_score": None,
    }

    if quiz_scores:
        stats["average_quiz_score"] = round(
            sum(quiz_scores.values()) / len(quiz_scores), 1
        )

    if recall_scores:
        stats["average_recall_score"] = round(
            sum(recall_scores.values()) / len(recall_scores), 1
        )

    return stats
```

**Step 5: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestUpdateProgress -v`

Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add tests/ tools/edps/progress.py
git commit -m "feat: add progress.yaml update logic with tests"
```

---

## Task 7: Hook Runner - Test and Implementation

**Files:**
- Modify: `tests/test_progress.py`
- Modify: `tools/edps/progress.py`

**Step 1: Write failing test for hook runner**

Add to `tests/test_progress.py`:

```python
from edps.progress import run_hook


class TestRunHook:
    """Tests for run_hook function (main entry point)."""

    def test_updates_progress_for_staged_files(self, tmp_path):
        """Should detect completion and update progress.yaml."""
        # Setup: create book structure
        book_dir = tmp_path / "books" / "test-book"
        section_dir = book_dir / "sections" / "001"
        section_dir.mkdir(parents=True)

        # Copy complete fixtures
        shutil.copy(FIXTURES / "recall_complete.md", section_dir / "recall.md")
        shutil.copy(FIXTURES / "quiz_complete.md", section_dir / "quiz.md")

        # Create initial progress.yaml
        shutil.copy(FIXTURES / "progress_initial.yaml", book_dir / "progress.yaml")

        # Act: run hook with staged files
        staged = ["books/test-book/sections/001/recall.md"]
        modified = run_hook(staged, base_path=tmp_path)

        # Assert: progress was updated
        assert len(modified) == 1
        assert modified[0] == book_dir / "progress.yaml"

        progress = yaml.safe_load((book_dir / "progress.yaml").read_text())
        assert "001" in progress["completed_sections"]
        assert progress["quiz_scores"]["001"] == 7

    def test_no_update_for_incomplete_section(self, tmp_path):
        """Should not add to completed_sections if section incomplete."""
        # Setup: create book structure with incomplete quiz
        book_dir = tmp_path / "books" / "test-book"
        section_dir = book_dir / "sections" / "001"
        section_dir.mkdir(parents=True)

        shutil.copy(FIXTURES / "recall_complete.md", section_dir / "recall.md")
        shutil.copy(FIXTURES / "quiz_partial.md", section_dir / "quiz.md")
        shutil.copy(FIXTURES / "progress_initial.yaml", book_dir / "progress.yaml")

        # Act
        staged = ["books/test-book/sections/001/recall.md"]
        run_hook(staged, base_path=tmp_path)

        # Assert: not marked complete
        progress = yaml.safe_load((book_dir / "progress.yaml").read_text())
        assert "001" not in progress["completed_sections"]
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestRunHook -v`

Expected: FAIL with "cannot import name 'run_hook'"

**Step 3: Add run_hook to progress.py**

Add to `tools/edps/progress.py`:

```python
def run_hook(staged_files: list[str], base_path: Path = None) -> list[Path]:
    """
    Main hook entry point.

    1. Parse staged files to find affected (book, section) pairs
    2. Check each affected section for completion
    3. Update progress.yaml for each affected book

    Args:
        staged_files: List of staged file paths (relative to repo root)
        base_path: Base path of repository (default: current directory)

    Returns:
        List of modified progress.yaml paths (for auto-staging)
    """
    if base_path is None:
        base_path = Path.cwd()

    # Parse staged files
    affected = parse_staged_files(staged_files)

    if not affected:
        return []

    modified_files = []

    for book_slug, section_ids in affected.items():
        book_path = base_path / "books" / book_slug

        if not book_path.exists():
            continue

        # Check each affected section
        section_updates = {}
        for section_id in section_ids:
            section_path = book_path / "sections" / section_id
            if section_path.exists():
                status = check_section_completion(section_path)
                section_updates[section_id] = status

        if section_updates:
            update_progress(book_path, section_updates)
            modified_files.append(book_path / "progress.yaml")

    return modified_files
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py::TestRunHook -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add tests/test_progress.py tools/edps/progress.py
git commit -m "feat: add hook runner entry point with tests"
```

---

## Task 8: CLI Commands - sync and init-hooks

**Files:**
- Create: `tools/edps/commands/sync.py`
- Create: `tools/edps/commands/hooks.py`
- Modify: `tools/edps/cli.py`

**Step 1: Create sync command**

```python
# tools/edps/commands/sync.py
"""Sync command - manually update progress from homework files."""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from edps.progress import (
    check_section_completion,
    update_progress,
    parse_staged_files,
)

console = Console()


def sync(
    book_slug: Optional[str] = typer.Argument(
        None,
        help="Book slug to sync (e.g., 'wealth-of-nations'). Omit for --all.",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Rescan all sections (not just recent changes)",
    ),
    all_books: bool = typer.Option(
        False,
        "--all",
        help="Sync all books",
    ),
    books_dir: Optional[Path] = typer.Option(
        None,
        "--books-dir",
        help="Path to books directory",
    ),
) -> None:
    """Sync progress.yaml from homework files."""
    if books_dir is None:
        books_dir = Path.cwd() / "books"

    if not books_dir.exists():
        console.print(f"[red]Error:[/red] Books directory not found: {books_dir}")
        raise typer.Exit(1)

    # Determine which books to sync
    if all_books:
        book_slugs = [
            d.name for d in books_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]
    elif book_slug:
        book_slugs = [book_slug]
    else:
        console.print("[red]Error:[/red] Specify a book slug or use --all")
        raise typer.Exit(1)

    for slug in book_slugs:
        book_path = books_dir / slug
        sections_path = book_path / "sections"

        if not sections_path.exists():
            console.print(f"[yellow]Skipping {slug}:[/yellow] No sections directory")
            continue

        console.print(f"[blue]Syncing:[/blue] {slug}")

        # Check all sections
        section_updates = {}
        for section_dir in sorted(sections_path.iterdir()):
            if section_dir.is_dir():
                status = check_section_completion(section_dir)
                section_updates[section_dir.name] = status

                if status.is_complete:
                    console.print(f"  [green]✓[/green] {section_dir.name}")
                else:
                    console.print(f"  [dim]○[/dim] {section_dir.name}")

        # Update progress
        update_progress(book_path, section_updates)

        completed = sum(1 for s in section_updates.values() if s.is_complete)
        console.print(
            f"[green]Done:[/green] {completed}/{len(section_updates)} sections complete"
        )
```

**Step 2: Create hooks command**

```python
# tools/edps/commands/hooks.py
"""Hooks command - install git hooks."""
import stat
from pathlib import Path

import typer
from rich.console import Console

console = Console()

HOOK_SCRIPT = '''#!/bin/bash
set -e

# Get staged files
STAGED=$(git diff --cached --name-only)

if [ -z "$STAGED" ]; then
    exit 0
fi

# Run progress sync on staged files
MODIFIED=$(python -m edps.progress --hook <<< "$STAGED" 2>/dev/null || true)

# Auto-stage any modified progress files
if [ -n "$MODIFIED" ]; then
    echo "$MODIFIED" | while read -r file; do
        if [ -n "$file" ] && [ -f "$file" ]; then
            git add "$file"
            echo "Auto-staged: $file"
        fi
    done
fi
'''


def init_hooks(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite existing pre-commit hook",
    ),
) -> None:
    """Install the EDPS pre-commit hook."""
    # Find .git directory
    git_dir = Path.cwd() / ".git"
    if not git_dir.exists():
        console.print("[red]Error:[/red] Not a git repository")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists() and not force:
        console.print(f"[yellow]Warning:[/yellow] {hook_path} already exists")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Write hook
    hook_path.write_text(HOOK_SCRIPT)

    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    console.print(f"[green]✓[/green] Installed pre-commit hook: {hook_path}")
    console.print("[dim]Progress will auto-sync on each commit[/dim]")
```

**Step 3: Add CLI entry point for --hook mode in progress.py**

Add to end of `tools/edps/progress.py`:

```python
def main():
    """CLI entry point for hook mode."""
    import sys

    if "--hook" in sys.argv:
        # Read staged files from stdin
        staged = sys.stdin.read().strip().split("\n")
        staged = [f for f in staged if f]  # Remove empty lines

        modified = run_hook(staged)

        # Print modified files for the hook to stage
        for path in modified:
            print(path)


if __name__ == "__main__":
    main()
```

**Step 4: Update cli.py to register new commands**

Modify `tools/edps/cli.py`:

```python
"""EDPS Method CLI - Main entry point."""
import typer

from edps.commands.init import init as init_command
from edps.commands.ingest import ingest as ingest_command
from edps.commands.generate import generate as generate_command
from edps.commands.run import run as run_command
from edps.commands.sync import sync as sync_command
from edps.commands.hooks import init_hooks as init_hooks_command

app = typer.Typer(
    name="edps",
    help="EDPS Method automation CLI",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show version."""
    typer.echo("edps v0.1.0")


app.command(name="init")(init_command)
app.command(name="ingest")(ingest_command)
app.command(name="generate")(generate_command)
app.command(name="run")(run_command)
app.command(name="sync")(sync_command)
app.command(name="init-hooks")(init_hooks_command)


if __name__ == "__main__":
    app()
```

**Step 5: Test CLI commands manually**

```bash
# Test sync command
edps sync wealth-of-nations

# Test init-hooks command
edps init-hooks
```

**Step 6: Commit**

```bash
git add tools/edps/commands/sync.py tools/edps/commands/hooks.py tools/edps/cli.py tools/edps/progress.py
git commit -m "feat: add sync and init-hooks CLI commands"
```

---

## Task 9: Integration Test

**Files:**
- Modify: `tests/test_progress.py`

**Step 1: Write integration test**

Add to `tests/test_progress.py`:

```python
import subprocess


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_full_workflow(self, tmp_path):
        """Test complete flow: files -> sync -> progress updated."""
        # Setup: create realistic book structure
        book_dir = tmp_path / "books" / "test-book"

        for section_id in ["001", "002", "003"]:
            section_dir = book_dir / "sections" / section_id
            section_dir.mkdir(parents=True)

            # 001: complete
            if section_id == "001":
                shutil.copy(FIXTURES / "recall_complete.md", section_dir / "recall.md")
                shutil.copy(FIXTURES / "quiz_complete.md", section_dir / "quiz.md")
            # 002: partial (recall done, quiz not)
            elif section_id == "002":
                shutil.copy(FIXTURES / "recall_complete.md", section_dir / "recall.md")
                shutil.copy(FIXTURES / "quiz_partial.md", section_dir / "quiz.md")
            # 003: not started
            else:
                shutil.copy(FIXTURES / "recall_template.md", section_dir / "recall.md")
                shutil.copy(FIXTURES / "quiz_template.md", section_dir / "quiz.md")

        # Create initial progress
        shutil.copy(FIXTURES / "progress_initial.yaml", book_dir / "progress.yaml")

        # Act: simulate hook run for all sections
        staged = [
            "books/test-book/sections/001/recall.md",
            "books/test-book/sections/002/recall.md",
            "books/test-book/sections/003/recall.md",
        ]
        run_hook(staged, base_path=tmp_path)

        # Assert
        progress = yaml.safe_load((book_dir / "progress.yaml").read_text())

        # Only 001 should be complete
        assert progress["completed_sections"] == ["001"]
        assert progress["quiz_scores"] == {"001": 7}
        assert progress["recall_scores"] == {"001": 4}
        assert progress["stats"]["total_sections_completed"] == 1
        assert progress["stats"]["average_quiz_score"] == 7.0
        assert progress["stats"]["average_recall_score"] == 4.0
```

**Step 2: Run all tests**

Run: `PYTHONPATH="$PWD/tools" python -m pytest tests/test_progress.py -v`

Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_progress.py
git commit -m "test: add integration test for full workflow"
```

---

## Task 10: Final Verification and Documentation

**Files:**
- Modify: `README.md`

**Step 1: Run full test suite**

```bash
PYTHONPATH="$PWD/tools" python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS

**Step 2: Manual end-to-end test**

```bash
# Install hooks
edps init-hooks

# Make a change to a completed section
# (edit books/wealth-of-nations/sections/001/recall.md)

# Commit and verify progress updates
git add books/wealth-of-nations/sections/001/
git commit -m "test: verify hook works"

# Check progress was updated
cat books/wealth-of-nations/progress.yaml
```

**Step 3: Update README with new commands**

Add to README.md under "Quick Start" or new section:

```markdown
### Automatic Progress Tracking

Progress is tracked automatically via git hooks:

```bash
# One-time setup
edps init-hooks
```

After setup, `progress.yaml` updates automatically when you commit homework files.

#### Manual Sync

```bash
# Sync a specific book
edps sync wealth-of-nations

# Rescan all sections
edps sync wealth-of-nations --full

# Sync all books
edps sync --all
```
```

**Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: add automatic progress tracking to README"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Create test fixtures | N/A |
| 2 | Recall detection | 3 |
| 3 | Quiz detection | 3 |
| 4 | Section detection | 3 |
| 5 | Path parsing | 4 |
| 6 | Progress update | 3 |
| 7 | Hook runner | 2 |
| 8 | CLI commands | Manual |
| 9 | Integration test | 1 |
| 10 | Final verification | Manual |

**Total: 19 automated tests + manual verification**
