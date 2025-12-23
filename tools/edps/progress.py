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
