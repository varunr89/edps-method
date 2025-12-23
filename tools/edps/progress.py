"""Progress detection and sync module."""
import re
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RecallResult:
    """Result of checking recall completion."""
    is_complete: bool
    score: Optional[int]


@dataclass
class QuizResult:
    """Result of checking quiz completion."""
    is_complete: bool
    score: Optional[int]


@dataclass
class SectionStatus:
    """Result of checking section completion."""
    is_complete: bool
    recall_score: Optional[int]
    quiz_score: Optional[int]


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
