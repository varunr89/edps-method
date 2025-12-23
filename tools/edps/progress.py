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


@dataclass
class QuizResult:
    """Result of checking quiz completion."""
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
