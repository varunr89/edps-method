"""AI-powered evaluation of recall and quiz answers."""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal, Optional
import re
import json


@dataclass
class AnswerFeedback:
    """Feedback for a single answer or recall point."""
    label: str  # Display label (e.g., "Q1: Main Claim")
    correct: bool
    note: Optional[str] = None  # Keep for backward compat
    score: Optional[float] = None  # For quiz questions
    # New fields for v1 schema:
    question_id: Optional[str] = None  # Stable identifier (e.g., "q1", "recall_main")
    explanation: Optional[str] = None  # Clearer name (will replace note in v1)
    accuracy: Optional[str] = None  # Factual correctness analysis
    reasoning: Optional[str] = None  # Logic and argument analysis
    writing: Optional[str] = None  # Prose quality analysis


@dataclass
class RecallFeedback:
    """Complete feedback for recall.md evaluation."""
    points: list[AnswerFeedback]
    one_sentence_ok: bool
    one_sentence_note: str
    score: int  # 0-5
    reasoning: str


@dataclass
class WritingScores:
    """Writing craft scores (1-5 each)."""
    precision: int
    clarity: int
    economy: int
    suggestion: str  # One concrete fix to practice


@dataclass
class ThematicInsights:
    """Cross-answer thematic patterns."""
    source_mastery: str
    reasoning_quality: str
    writing_craft: WritingScores


@dataclass
class QuizFeedback:
    """Complete feedback for quiz.md evaluation."""
    schema_version: Literal["v0", "v1"] = "v1"  # Version for migration support
    answers: list[AnswerFeedback] = field(default_factory=list)
    total_score: float = 0.0  # 0-8
    reasoning: str = ""  # Legacy field, kept for backward compat
    thematic_insights: Optional[ThematicInsights] = None
    tutors_note: Optional[str] = None
    model_id: Optional[str] = None  # Which LLM produced this evaluation
    created_at: Optional[str] = None  # ISO timestamp


@dataclass
class EvaluationResult:
    """Result of evaluating a section's recall and quiz."""
    recall_score: int
    quiz_score: float
    recall_feedback: RecallFeedback
    quiz_feedback: QuizFeedback


def migrate_v0_to_v1(data: dict) -> dict:
    """Migrate v0 evaluation schema to v1.

    Changes:
    - Adds schema_version: "v1"
    - Maps 'note' -> 'explanation'
    - Adds question_id from label or index
    """
    # Check if already v1
    if data.get("quiz", {}).get("schema_version") == "v1":
        return data

    result = {"recall": data.get("recall", {}), "quiz": {}}
    quiz = data.get("quiz", {})

    # Migrate answers
    migrated_answers = []
    for i, answer in enumerate(quiz.get("answers", [])):
        migrated = {
            "question_id": f"q{i+1}",
            "label": answer.get("label", f"Q{i+1}"),
            "correct": answer.get("correct", False),
            "explanation": answer.get("note", ""),  # note -> explanation
            "score": answer.get("score"),
            "accuracy": answer.get("accuracy"),
            "reasoning": answer.get("reasoning"),
            "writing": answer.get("writing"),
        }
        migrated_answers.append(migrated)

    result["quiz"] = {
        "schema_version": "v1",
        "answers": migrated_answers,
        "total_score": quiz.get("total_score", 0),
        "reasoning": quiz.get("reasoning", ""),
        "thematic_insights": quiz.get("thematic_insights"),
        "tutors_note": quiz.get("tutors_note"),
    }

    return result


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


# Recall section labels from the EDPS template
RECALL_SECTION_LABELS = [
    ("Main Claim", "What was the core argument? (should match source)"),
    ("Key Mechanism", "What process or cause-effect was described? (should match source)"),
    ("Example", "What example stuck with them? (should match source)"),
    ("Modern Parallel", "What connection to today came to mind? (EXTERNAL connections expected and correct)"),
    ("Uncertainty", "What are they unsure about? (questions/confusion expected)"),
]


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

    # Build recall points with section labels
    recall_points_formatted = []
    for i, point in enumerate(recall_data['memory_points']):
        if i < len(RECALL_SECTION_LABELS):
            label, guidance = RECALL_SECTION_LABELS[i]
            recall_points_formatted.append(f"{i+1}. **{label}**: {point}\n   _{guidance}_")
        else:
            recall_points_formatted.append(f"{i+1}. {point}")

    prompt = f"""You are evaluating a student's understanding of a text using the EDPS Method (spaced repetition + active recall).

# Source Text
{source_text}

# Student's Recall (from memory, before re-reading)

## Memory Points
{chr(10).join(recall_points_formatted)}

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

Provide comprehensive feedback on the student's work. Return as JSON:

```json
{
  "recall": {
    "points": [
      {
        "label": "Point description",
        "correct": true,
        "note": "Brief note (legacy)",
        "accuracy": "What they got right/wrong factually",
        "reasoning": "How their logic holds up",
        "writing": "Prose quality feedback with specific suggestions"
      }
    ],
    "one_sentence_ok": true,
    "one_sentence_note": "Feedback on summary",
    "score": 0,
    "reasoning": "Overall assessment"
  },
  "quiz": {
    "answers": [
      {
        "label": "Q1: Title",
        "correct": true,
        "score": 1,
        "note": "Brief note (legacy)",
        "accuracy": "Factual correctness analysis",
        "reasoning": "Logic and argument analysis",
        "writing": "Prose quality: precision, clarity, economy"
      }
    ],
    "total_score": 8,
    "reasoning": "Legacy overall assessment",
    "thematic_insights": {
      "source_mastery": "Patterns across answers—what they consistently get/miss. Cite specific examples.",
      "reasoning_quality": "How they build arguments. Logical gaps. Strengths. Edges to develop.",
      "writing_craft": {
        "precision": 4,
        "clarity": 4,
        "economy": 3,
        "suggestion": "One concrete fix to practice"
      }
    },
    "tutors_note": "Narrative synthesis (3-4 paragraphs): What they're doing well, 2-3 things to carry forward with depth, prompt for next section."
  }
}
```

## Scoring & Feedback Guidelines

**Scoring Rubric:**
- Recall score (0-5): Based on accuracy and completeness of memory points
  - Points 1-3 (Main Claim, Key Mechanism, Example): Evaluate against source text
  - Point 4 (Modern Parallel): External connections are EXPECTED and CORRECT - evaluate thoughtfulness, not source accuracy
  - Point 5 (Uncertainty): Questions/confusion are EXPECTED - evaluate self-awareness, not source accuracy
- Quiz scores: Each question worth 1 point (8 total questions)
- Mark partial credit as 0.5 when applicable
- Use booleans as true/false, no trailing commas

**Per-Answer Analysis:**
- **Accuracy:** Did they capture what the source actually says? Quote specifics.
- **Reasoning:** Is their causal logic sound? Do they identify correct relationships?
- **Writing:**
  - Precision: Do they use the author's key terms correctly?
  - Clarity: Do they lead with main points? Is structure clear?
  - Economy: Can they say it in fewer words without losing meaning?

Keep per-answer explanations to 1-3 sentences; depth goes in thematic_insights and tutors_note.

**Thematic Insights:**
- Identify PATTERNS across all answers, not just per-question issues
- Be specific: "You wrote X but Smith says Y" not "some inaccuracies"
- writing_craft scores are 1-5 each

**Tutor's Note:**
- Open with genuine praise backed by evidence
- Give 2-3 actionable insights with depth (why it matters, how to apply)
- Close with what to watch for in the next section

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

    # Build RecallFeedback with optional new fields
    recall_data = data["recall"]
    recall_points = [
        AnswerFeedback(
            label=p["label"],
            correct=p["correct"],
            note=p.get("note"),
            accuracy=p.get("accuracy"),
            reasoning=p.get("reasoning"),
            writing=p.get("writing"),
        )
        for p in recall_data["points"]
    ]
    recall_feedback = RecallFeedback(
        points=recall_points,
        one_sentence_ok=recall_data["one_sentence_ok"],
        one_sentence_note=recall_data["one_sentence_note"],
        score=recall_data["score"],
        reasoning=recall_data["reasoning"],
    )

    # Build QuizFeedback with optional new fields
    quiz_data = data["quiz"]
    quiz_answers = [
        AnswerFeedback(
            label=a["label"],
            correct=a["correct"],
            note=a.get("note"),
            score=a.get("score"),
            accuracy=a.get("accuracy"),
            reasoning=a.get("reasoning"),
            writing=a.get("writing"),
        )
        for a in quiz_data["answers"]
    ]

    # Parse thematic insights if present
    thematic_insights = None
    if "thematic_insights" in quiz_data:
        ti = quiz_data["thematic_insights"]
        wc = ti["writing_craft"]
        thematic_insights = ThematicInsights(
            source_mastery=ti["source_mastery"],
            reasoning_quality=ti["reasoning_quality"],
            writing_craft=WritingScores(
                precision=wc["precision"],
                clarity=wc["clarity"],
                economy=wc["economy"],
                suggestion=wc["suggestion"],
            ),
        )

    quiz_feedback = QuizFeedback(
        answers=quiz_answers,
        total_score=quiz_data["total_score"],
        reasoning=quiz_data["reasoning"],
        thematic_insights=thematic_insights,
        tutors_note=quiz_data.get("tutors_note"),
    )

    return recall_feedback, quiz_feedback


def format_recall_feedback(feedback: RecallFeedback, eval_date: str, source_file: str) -> str:
    """Format recall feedback as expanded markdown.

    Args:
        feedback: RecallFeedback object with evaluation results
        eval_date: Date of evaluation (YYYY-MM-DD format)
        source_file: Path to source file being evaluated

    Returns:
        Markdown-formatted feedback with per-point analysis and metadata
    """
    lines = [
        "---",
        "",
        "## AI Feedback on Recall",
        "",
        f"**Evaluated:** {eval_date} | **Source:** {source_file}",
        f"**Score:** {feedback.score}/5",
        "",
        "---",
        "",
        "### Recall Points",
        "",
    ]

    for point in feedback.points:
        status = "✓" if point.correct else "⚠️"
        lines.append(f"#### {point.label} {status}")
        lines.append("")

        if point.accuracy:
            lines.append(f"**Accuracy:** {point.accuracy}")
        if point.reasoning:
            lines.append(f"**Reasoning:** {point.reasoning}")
        if point.writing:
            lines.append(f"**Writing:** {point.writing}")

        # Fallback to legacy note if no expanded fields
        if not (point.accuracy or point.reasoning or point.writing):
            if point.note:
                lines.append(f"**Feedback:** {point.note}")

        lines.append("")

    # One sentence summary section
    lines.extend([
        "---",
        "",
        "### One Sentence Summary",
        "",
        f"**Status:** {'✓ Approved' if feedback.one_sentence_ok else '⚠️ Needs Work'}",
        "",
        f"**Feedback:** {feedback.one_sentence_note}",
        "",
        "---",
        "",
        "### Overall Assessment",
        "",
        feedback.reasoning,
    ])

    return "\n".join(lines)


def format_quiz_feedback(feedback: QuizFeedback, eval_date: str, source_file: str) -> str:
    """Format quiz feedback as expanded markdown.

    Args:
        feedback: QuizFeedback object with evaluation results
        eval_date: Date of evaluation (YYYY-MM-DD format)
        source_file: Path to source file being evaluated

    Returns:
        Markdown-formatted feedback with per-answer analysis, thematic insights,
        and tutor's note
    """
    lines = [
        "---",
        "",
        "## AI Feedback",
        "",
        f"**Evaluated:** {eval_date} | **Source:** {source_file}",
        f"**Total Score:** {feedback.total_score}/8",
        "",
        "---",
        "",
        "### Per-Answer Analysis",
        "",
    ]

    for answer in feedback.answers:
        status = "✓" if answer.correct else "⚠️"
        score_str = f"{answer.score:.1f}/1.0" if answer.score is not None else ""
        lines.append(f"#### {answer.label} ({score_str}) {status}")
        lines.append("")

        if answer.accuracy:
            lines.append(f"**Accuracy:** {answer.accuracy}")
        if answer.reasoning:
            lines.append(f"**Reasoning:** {answer.reasoning}")
        if answer.writing:
            lines.append(f"**Writing:** {answer.writing}")

        # Fallback to legacy note if no expanded fields
        if not (answer.accuracy or answer.reasoning or answer.writing):
            lines.append(f"**Feedback:** {answer.note}")

        lines.append("")

    # Thematic insights
    if feedback.thematic_insights:
        ti = feedback.thematic_insights
        wc = ti.writing_craft
        lines.extend([
            "---",
            "",
            "### Thematic Insights",
            "",
            "#### Source Mastery",
            ti.source_mastery,
            "",
            "#### Reasoning Quality",
            ti.reasoning_quality,
            "",
            "#### Writing Craft",
            f"**Precision:** {wc.precision}/5 | **Clarity:** {wc.clarity}/5 | **Economy:** {wc.economy}/5",
            "",
            f"**Practice:** {wc.suggestion}",
            "",
        ])

    # Tutor's note
    if feedback.tutors_note:
        lines.extend([
            "---",
            "",
            "### Tutor's Note",
            "",
            feedback.tutors_note,
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

    # Check if council is enabled for evaluation
    if config.council.enabled and "evaluation" in config.council.tasks:
        from edps.core.council import Council
        # Resolve role names to actual model names from models config
        resolved_models = config.council.resolve_models(config.models)
        resolved_chair = config.council.resolve_chair(config.models)
        council = Council(
            models=resolved_models,
            chair=resolved_chair,
            stages=config.council.stages,
        )
        council_result = council.run(prompt, client)
        response_content = council_result.final_answer
    else:
        response = client.complete(prompt, model=config.models.evaluation, max_tokens=config.defaults.max_tokens)
        response_content = response.content

    # Parse response
    recall_feedback, quiz_feedback = parse_evaluation_response(response_content)

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
