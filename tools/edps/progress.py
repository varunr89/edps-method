"""Progress detection and sync module."""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML


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
    quiz_score: Optional[float]


def check_recall_completion(recall_path: Path) -> RecallResult:
    """
    Check if a recall.md file is complete.

    Complete when:
    - "From Memory" section has actual content (numbered points)
    - No [Your answer] placeholders remain in content sections

    Score is extracted if present but NOT required for completion
    (AI evaluation will provide the score).

    Returns RecallResult with completion status and extracted score.
    """
    if not recall_path.exists():
        return RecallResult(is_complete=False, score=None)

    text = recall_path.read_text(encoding="utf-8")

    # Check for content placeholders (not metadata like [X minutes])
    has_answer_placeholders = "[Your answer]" in text

    # Check if "From Memory" section has actual content
    # Look for content after "## From Memory" section header (with optional suffix)
    memory_section = re.search(
        r"## From Memory[^\n]*\n([\s\S]*?)(?=\n---|\n## |$)",
        text
    )
    has_memory_content = False
    if memory_section:
        content = memory_section.group(1)
        # Look for either:
        # 1. Numbered list items: "1. actual content"
        # 2. Numbered headers with content below: "### 1. Title\ncontent"
        numbered_points = re.findall(r"^\d+\.\s+(.+)$", content, re.MULTILINE)
        # For headers, look for ### N. Title followed by non-empty lines
        header_content = re.findall(r"###\s+\d+\.[^\n]*\n([^\n#]+)", content)

        # Filter out template placeholders
        real_points = [p for p in numbered_points if not p.startswith("[")]
        real_content = [h.strip() for h in header_content if h.strip() and not h.strip().startswith("[")]

        has_memory_content = len(real_points) >= 1 or len(real_content) >= 1

    # Extract score if present (for display, not required)
    score = None
    score_pattern = r"\*\*My score\*\*:\s*\[(\d+)\]\s*/\s*5"
    score_match = re.search(score_pattern, text)
    if score_match:
        score = int(score_match.group(1))
    else:
        legacy_pattern = r"-\s*Recall accuracy:\s*\[(\d+)\]"
        legacy_match = re.search(legacy_pattern, text)
        if legacy_match:
            score = int(legacy_match.group(1))

    # Complete if has memory content and no answer placeholders
    is_complete = has_memory_content and not has_answer_placeholders

    return RecallResult(is_complete=is_complete, score=score)


def check_quiz_completion(quiz_path: Path) -> QuizResult:
    """
    Check if a quiz.md file is complete.

    Complete when:
    - All **Answer:** sections have non-whitespace text

    Score is extracted if present but NOT required for completion
    (AI evaluation will provide the score).

    Returns QuizResult with completion status and extracted score.
    """
    if not quiz_path.exists():
        return QuizResult(is_complete=False, score=None)

    text = quiz_path.read_text(encoding="utf-8")

    # Split by **Answer:** and check each following section has content
    parts = re.split(r"\*\*Answer:\*\*", text)
    all_answers_filled = True
    answer_count = 0

    for part in parts[1:]:  # Skip content before first Answer
        answer_count += 1
        # Get content before next section marker
        content_match = re.match(r"(.*?)(?=\n---|\n###|\n##|\Z)", part, re.DOTALL)
        if content_match:
            answer_content = content_match.group(1).strip()
            if not answer_content or answer_content == "[Your answer]":
                all_answers_filled = False
                break

    # Extract total score if present (for display, not required)
    total_pattern = r"\*\*Total:\s*(\d+)\s*/\s*\d+\*\*"
    total_match = re.search(total_pattern, text)
    score = int(total_match.group(1)) if total_match else None

    # Complete if all answers are filled (score not required - AI will provide it)
    is_complete = all_answers_filled and answer_count > 0

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
    - Preserves comments and formatting

    Args:
        book_path: Path to the book directory (contains progress.yaml)
        section_updates: Dict mapping section_id to SectionStatus
    """
    progress_file = book_path / "progress.yaml"

    # Use ruamel.yaml to preserve comments
    yaml = YAML()
    yaml.preserve_quotes = True

    # Load existing or create default
    if progress_file.exists():
        with open(progress_file) as f:
            progress = yaml.load(f) or {}
    else:
        progress = {}

    # Ensure required keys exist
    if "completed_sections" not in progress:
        progress["completed_sections"] = []
    if "quiz_scores" not in progress:
        progress["quiz_scores"] = {}
    if "recall_scores" not in progress:
        progress["recall_scores"] = {}
    if "stats" not in progress:
        progress["stats"] = {}

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
            if section_id in progress["quiz_scores"]:
                del progress["quiz_scores"][section_id]
            if section_id in progress["recall_scores"]:
                del progress["recall_scores"][section_id]

    # Sort completed_sections for consistency
    progress["completed_sections"] = sorted(progress["completed_sections"])

    # Recalculate stats (update in place to preserve structure)
    new_stats = _calculate_stats(progress)
    for key, value in new_stats.items():
        progress["stats"][key] = value

    # Write back preserving comments
    with open(progress_file, "w") as f:
        yaml.dump(progress, f)


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


def run_hook(staged_files: list[str], base_path: Path = None, do_eval: bool = False) -> list[Path]:
    """
    Main hook entry point.

    1. Parse staged files to find affected (book, section) pairs
    2. Check each affected section for completion
    3. Optionally run AI evaluation on complete sections
    4. Update progress.yaml for each affected book

    Args:
        staged_files: List of staged file paths (relative to repo root)
        base_path: Base path of repository (default: current directory)
        do_eval: If True, run AI evaluation on complete sections

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

                # If evaluation is enabled and section is complete, run AI evaluation
                if do_eval and status.is_complete:
                    try:
                        from edps.config import load_config
                        from edps.evaluation import evaluate_section
                        config = load_config()
                        result = evaluate_section(section_path, book_slug, section_id, config)
                        # Update status with evaluation scores
                        status = SectionStatus(
                            is_complete=True,
                            recall_score=result.recall_score,
                            quiz_score=result.quiz_score
                        )
                    except Exception:
                        # If evaluation fails, keep original status
                        pass

                section_updates[section_id] = status

        if section_updates:
            update_progress(book_path, section_updates)
            modified_files.append(book_path / "progress.yaml")

    return modified_files


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


if __name__ == "__main__":
    main()
