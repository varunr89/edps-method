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


def parse_quiz_content(content: str) -> dict:
    """Parse quiz.md content into structured data.

    Args:
        content: Raw markdown content of quiz.md

    Returns:
        Dict with qa_pairs list, each containing number, title, question, and answer
    """
    result = {"qa_pairs": []}
    pattern = r"### (\d+)\. (.+?)\n\n(.+?)\n\n\*\*Answer:\*\*\s*(.+?)(?=\n---|\n###|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)
    for match in matches:
        result["qa_pairs"].append({
            "number": match[0],
            "title": match[1].strip(),
            "question": match[2].strip(),
            "answer": match[3].strip(),
        })
    return result


def build_evaluation_prompt(source_text: str, recall_content: str, quiz_content: str) -> str:
    """Build a prompt for Claude to evaluate recall and quiz answers.

    Args:
        source_text: The original source material
        recall_content: Raw markdown content of recall.md
        quiz_content: Raw markdown content of quiz.md

    Returns:
        A prompt string that requests JSON-formatted evaluation
    """
    recall_data = parse_recall_content(recall_content)
    quiz_data = parse_quiz_content(quiz_content)

    prompt = f"""You are evaluating a student's understanding of a text using the EDPS Method (spaced repetition + active recall).

# Source Text
{source_text}

# Student's Recall (from memory, before re-reading)

## Memory Points
{chr(10).join(f'{i+1}. {point}' for i, point in enumerate(recall_data['memory_points']))}

## One Sentence Summary
{recall_data['one_sentence']}

# Student's Quiz Answers

"""

    for qa in quiz_data['qa_pairs']:
        prompt += f"**Q{qa['number']}: {qa['title']}**\n"
        prompt += f"Question: {qa['question']}\n"
        prompt += f"Answer: {qa['answer']}\n\n"

    prompt += """
# Evaluation Task

Please evaluate the student's recall and quiz performance. Return your evaluation in JSON format:

```json
{
  "recall": {
    "points": [
      {"label": "Point description", "correct": true/false, "note": "Feedback"}
    ],
    "one_sentence_ok": true/false,
    "one_sentence_note": "Feedback on summary",
    "score": 0-5,
    "reasoning": "Overall assessment"
  },
  "quiz": {
    "answers": [
      {"label": "Q1: Title", "correct": true/false, "score": 0-1, "note": "Feedback"}
    ],
    "total_score": 0-8,
    "reasoning": "Overall assessment"
  }
}
```

Scoring rubric:
- Recall score (0-5): Based on accuracy and completeness of memory points
- Quiz scores: Each question worth 1 point (8 total questions)
- Mark partial credit as 0.5 when applicable

Respond ONLY with the JSON object, no other text."""

    return prompt
