"""Quiz question type definitions."""
from dataclasses import dataclass
from typing import Literal


@dataclass
class MCOption:
    """Single option in a multiple choice question."""
    letter: str  # A, B, C, D
    text: str
    is_correct: bool

    def __post_init__(self):
        if len(self.letter) != 1 or self.letter not in "ABCDEFGH":
            raise ValueError(f"Invalid option letter: {self.letter}")


@dataclass
class MCQuestion:
    """Multiple choice question with variable answer types."""
    question_id: str  # Stable identifier (e.g., "mcq1")
    number: int  # Display number
    question: str
    options: list[MCOption]  # Structured options (not tuples)
    answer_type: Literal["one", "multiple", "none"]

    def correct_count(self) -> int:
        return sum(1 for opt in self.options if opt.is_correct)

    def correct_letters(self) -> set[str]:
        return {opt.letter for opt in self.options if opt.is_correct}

    def __post_init__(self):
        # Validate answer_type matches options
        correct = self.correct_count()
        if self.answer_type == "none" and correct != 0:
            raise ValueError("answer_type='none' but has correct options")
        if self.answer_type == "one" and correct != 1:
            raise ValueError(f"answer_type='one' but has {correct} correct options")


@dataclass
class ProseQuestion:
    """Prose question with variable types."""
    question_id: str  # Stable identifier
    number: int
    question: str
    question_type: Literal["adversarial", "comparative", "socratic", "synthesis"]
    sentence_range: tuple[int, int]  # (min, max) sentences


def score_mcq_answer(gold: set[str], selected: set[str]) -> float:
    """Score MCQ answer using F1-based partial credit.

    Args:
        gold: Set of correct answer letters (e.g., {"A", "B", "D"})
        selected: Set of student's selected letters

    Returns:
        Score from 0.0 to 1.0 based on F1 formula.

    Scoring rules:
    - If both sets empty (none-of-the-above correct): 1.0
    - If gold empty but student selected: 0.0
    - Otherwise: F1 = 2*P*R / (P+R) where:
      - Precision P = |gold ∩ selected| / |selected|
      - Recall R = |gold ∩ selected| / |gold|
    """
    # Handle none-of-the-above case
    if not gold and not selected:
        return 1.0
    if not gold and selected:
        return 0.0
    if gold and not selected:
        return 0.0

    # Calculate F1
    intersection = gold & selected
    precision = len(intersection) / len(selected)
    recall = len(intersection) / len(gold)

    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return round(f1, 3)
