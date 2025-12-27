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
