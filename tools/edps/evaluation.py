"""AI-powered evaluation of recall and quiz answers."""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional
import re
import json


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


@dataclass
class EvaluationResult:
    """Result of evaluating a section's recall and quiz."""
    recall_score: int
    quiz_score: float
    recall_feedback: RecallFeedback
    quiz_feedback: QuizFeedback


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


def parse_evaluation_response(response: str) -> tuple[RecallFeedback, QuizFeedback]:
    """Parse JSON from LLM evaluation response.

    Args:
        response: Raw response from Claude (may include markdown code blocks)

    Returns:
        Tuple of (RecallFeedback, QuizFeedback) objects
    """
    # Extract JSON from markdown code block if present
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON
        json_match = re.search(r'(\{.*\})', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response

    # Parse JSON
    data = json.loads(json_str)

    # Build RecallFeedback
    recall_data = data["recall"]
    recall_points = [
        AnswerFeedback(
            label=p["label"],
            correct=p["correct"],
            note=p["note"]
        )
        for p in recall_data["points"]
    ]
    recall_feedback = RecallFeedback(
        points=recall_points,
        one_sentence_ok=recall_data["one_sentence_ok"],
        one_sentence_note=recall_data["one_sentence_note"],
        score=recall_data["score"],
        reasoning=recall_data["reasoning"]
    )

    # Build QuizFeedback
    quiz_data = data["quiz"]
    quiz_answers = [
        AnswerFeedback(
            label=a["label"],
            correct=a["correct"],
            note=a["note"],
            score=a["score"]
        )
        for a in quiz_data["answers"]
    ]
    quiz_feedback = QuizFeedback(
        answers=quiz_answers,
        total_score=quiz_data["total_score"],
        reasoning=quiz_data["reasoning"]
    )

    return recall_feedback, quiz_feedback


def format_recall_feedback(feedback: RecallFeedback, eval_date: str, source_file: str) -> str:
    """Format recall feedback as markdown.

    Args:
        feedback: RecallFeedback object with evaluation results
        eval_date: Date of evaluation (YYYY-MM-DD format)
        source_file: Path to source file being evaluated

    Returns:
        Markdown-formatted feedback with table and metadata
    """
    lines = [
        "---",
        "",
        "## AI Feedback",
        "",
        f"**Evaluation Date:** {eval_date}",
        f"**Source:** {source_file}",
        f"**Overall Score:** {feedback.score}/5",
        "",
        "### Memory Points",
        "",
        "| Point | Status | Feedback |",
        "|-------|--------|----------|"
    ]

    for point in feedback.points:
        status = "✓" if point.correct else "⚠️"
        lines.append(f"| {point.label} | {status} | {point.note} |")

    lines.extend([
        "",
        "### One Sentence Summary",
        "",
        f"**Status:** {'✓ Accurate' if feedback.one_sentence_ok else '⚠️ Needs work'}",
        f"**Feedback:** {feedback.one_sentence_note}",
        "",
        "### Overall Assessment",
        "",
        feedback.reasoning
    ])

    return "\n".join(lines)


def format_quiz_feedback(feedback: QuizFeedback, eval_date: str, source_file: str) -> str:
    """Format quiz feedback as markdown.

    Args:
        feedback: QuizFeedback object with evaluation results
        eval_date: Date of evaluation (YYYY-MM-DD format)
        source_file: Path to source file being evaluated

    Returns:
        Markdown-formatted feedback with table and metadata
    """
    lines = [
        "---",
        "",
        "## AI Feedback",
        "",
        f"**Evaluation Date:** {eval_date}",
        f"**Source:** {source_file}",
        f"**Total Score:** {feedback.total_score}/8",
        "",
        "### Answers",
        "",
        "| Question | Status | Score | Feedback |",
        "|----------|--------|-------|----------|"
    ]

    for answer in feedback.answers:
        status = "✓" if answer.correct else "⚠️"
        score_str = f"{answer.score:.1f}/1.0"
        lines.append(f"| {answer.label} | {status} | {score_str} | {answer.note} |")

    lines.extend([
        "",
        "### Overall Assessment",
        "",
        feedback.reasoning
    ])

    return "\n".join(lines)


def evaluate_section(
    section_path: Path,
    book_slug: str,
    section_id: str,
    config: Optional["EdpsConfig"] = None,
) -> EvaluationResult:
    """Evaluate a section's recall and quiz answers.

    Args:
        section_path: Path to the section directory
        book_slug: Book slug identifier (e.g., "wealth-of-nations")
        section_id: Section ID (e.g., "001")
        config: Optional EDPS configuration

    Returns:
        EvaluationResult with scores and feedback

    Raises:
        FileNotFoundError: If source file doesn't exist
    """
    if config is None:
        from edps.config import load_config
        config = load_config()

    # Find source file
    source_file = section_path / f"EDPS-{book_slug}-{section_id}.txt"
    if not source_file.exists():
        raise FileNotFoundError(f"Source file not found: {source_file}")
    source_text = source_file.read_text()

    # Read and parse recall/quiz
    recall_path = section_path / "recall.md"
    recall_raw = recall_path.read_text()
    recall_content = parse_recall_content(recall_raw)

    quiz_path = section_path / "quiz.md"
    quiz_raw = quiz_path.read_text()
    quiz_content = parse_quiz_content(quiz_raw)

    # Build prompt and call LLM
    prompt = build_evaluation_prompt(source_text, recall_raw, quiz_raw)

    from edps.core.llm import LLMClient
    client = LLMClient(config)
    response = client.complete(prompt, max_tokens=2000)

    # Parse response
    recall_feedback, quiz_feedback = parse_evaluation_response(response.content)

    # Format and append feedback
    eval_date = date.today().isoformat()
    recall_md = format_recall_feedback(recall_feedback, eval_date, source_file.name)
    quiz_md = format_quiz_feedback(quiz_feedback, eval_date, source_file.name)

    # Append to files (avoid duplicate)
    if "## AI Feedback" not in recall_raw:
        with open(recall_path, "a") as f:
            f.write(recall_md)

    if "## AI Feedback" not in quiz_raw:
        with open(quiz_path, "a") as f:
            f.write(quiz_md)

    return EvaluationResult(
        recall_score=recall_feedback.score,
        quiz_score=quiz_feedback.total_score,
        recall_feedback=recall_feedback,
        quiz_feedback=quiz_feedback,
    )
