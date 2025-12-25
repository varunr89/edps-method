"""AI-powered evaluation of recall and quiz answers."""
from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class AnswerFeedback:
    """Feedback for a single answer or recall point."""
    label: str
    correct: bool
    note: str
    score: Optional[float] = None  # For quiz questions


@dataclass
class RecallFeedback:
    """Complete feedback for recall.md evaluation."""
    points: list[AnswerFeedback]
    one_sentence_ok: bool
    one_sentence_note: str
    score: int  # 0-5
    reasoning: str


@dataclass
class QuizFeedback:
    """Complete feedback for quiz.md evaluation."""
    answers: list[AnswerFeedback]
    total_score: float  # 0-8
    reasoning: str


def parse_recall_content(content: str) -> dict:
    """Parse recall.md content into structured data.

    Args:
        content: Raw markdown content of recall.md

    Returns:
        Dict with memory_points (list[str]) and one_sentence (str)
    """
    result = {"memory_points": [], "one_sentence": ""}

    # Extract numbered points from "From Memory" section
    memory_match = re.search(
        r"## From Memory.*?\n\n.*?\n\n((?:\d+\..*?\n)+)",
        content,
        re.DOTALL
    )
    if memory_match:
        points_text = memory_match.group(1)
        points = re.findall(r"\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\Z)", points_text, re.DOTALL)
        result["memory_points"] = [p.strip() for p in points]

    # Extract one sentence summary
    sentence_match = re.search(
        r"## One Sentence.*?\n\n(.+?)(?=\n---|\n##|\Z)",
        content,
        re.DOTALL
    )
    if sentence_match:
        result["one_sentence"] = sentence_match.group(1).strip()

    return result
