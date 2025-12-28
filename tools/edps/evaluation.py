"""AI-powered evaluation of recall and quiz answers."""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal, Optional
import re
import json

from difflib import SequenceMatcher

from edps.core.prompts import load_prompt, render_prompt


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
class InlineError:
    """A single claim-level error with anchor text for injection."""
    quoted_text: str  # Exact substring from user's answer
    summary: str  # Brief label for <summary> tag
    feedback: str  # Natural prose feedback


@dataclass
class InlineAnswerFeedback:
    """Per-answer feedback with inline errors and optional writing note."""
    question_id: str
    label: str
    score: float
    errors: list[InlineError] = field(default_factory=list)
    writing_note: Optional[str] = None


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


def strip_feedback(content: str) -> str:
    """Remove all existing feedback annotations from quiz content.

    Removes:
    - All <details>...</details> blocks (inline annotations)
    - The ## Summary section at end of file

    Args:
        content: Raw quiz.md content

    Returns:
        Content with feedback stripped, ready for fresh annotations
    """
    # Remove all <details> blocks
    result = re.sub(r'<details>.*?</details>\n*', '', content, flags=re.DOTALL)

    # Remove ## Summary section at end of file
    result = re.sub(r'\n---\n\n## Summary.*', '', result, flags=re.DOTALL)

    return result


def inject_writing_note(answer: str, writing_note: Optional[str]) -> str:
    """Append writing feedback at end of an answer.

    Args:
        answer: The answer text
        writing_note: Holistic writing feedback with rewrite example, or None

    Returns:
        Answer with writing note appended, or unchanged if no note
    """
    if not writing_note:
        return answer

    note_html = f'''
<details>
<summary>Writing</summary>
{writing_note}
</details>'''

    return answer.rstrip() + note_html + "\n"


def find_best_match(content: str, quoted: str, threshold: float = 0.8) -> Optional[str]:
    """Find the best fuzzy match for quoted text in content.

    Uses sliding window approach to find substrings that match above threshold.

    Args:
        content: The full text to search in
        quoted: The text to find (may be slightly different)
        threshold: Minimum similarity ratio (0-1)

    Returns:
        The matching substring from content, or None if no match above threshold
    """
    if not quoted or not content:
        return None

    # Try exact match first
    if quoted in content:
        return quoted

    best_match = None
    best_ratio = threshold

    # Sliding window approach: try windows of similar length to quoted text
    window_sizes = [len(quoted), len(quoted) - 5, len(quoted) + 5]

    for window_size in window_sizes:
        if window_size <= 0 or window_size > len(content):
            continue

        for i in range(len(content) - window_size + 1):
            window = content[i:i + window_size]
            ratio = SequenceMatcher(None, quoted.lower(), window.lower()).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = window

    return best_match


def inject_error(content: str, error: "InlineError") -> str:
    """Inject a single error annotation after the quoted text.

    Uses exact matching first, then falls back to fuzzy matching if needed.

    Args:
        content: The answer text to annotate
        error: InlineError with quoted_text anchor and feedback

    Returns:
        Content with <details> block inserted after quoted text,
        or unchanged if quoted text not found (even with fuzzy matching)
    """
    # Try exact match first
    anchor = error.quoted_text
    if anchor not in content:
        # Fall back to fuzzy matching
        fuzzy_match = find_best_match(content, anchor)
        if fuzzy_match:
            anchor = fuzzy_match
        else:
            return content  # No match found, skip

    feedback_html = f'''
<details>
<summary>{error.summary}</summary>
{error.feedback}
</details>'''

    # Replace only first occurrence
    return content.replace(anchor, anchor + feedback_html, 1)


def inject_inline_feedback(content: str, feedbacks: list["InlineAnswerFeedback"]) -> str:
    """Inject inline feedback annotations into quiz content.

    For each answer:
    1. Inject error annotations after quoted text
    2. Append writing note at end of answer block

    Args:
        content: Raw quiz.md content
        feedbacks: List of InlineAnswerFeedback for each question

    Returns:
        Content with inline annotations injected
    """
    result = content

    for feedback in feedbacks:
        # Inject each error annotation
        for error in feedback.errors:
            result = inject_error(result, error)

        # Inject writing note - find answer section and append
        if feedback.writing_note:
            # Find pattern: **Answer:** ... until --- or ### or end
            # Insert writing note before the separator
            pattern = r'(\*\*Answer:\*\*.*?)(\n\n---|\n\n###|\Z)'

            def insert_note(match):
                answer_part = match.group(1)
                separator = match.group(2) if match.group(2) else ''
                note_block = f'''
<details>
<summary>Writing</summary>
{feedback.writing_note}
</details>
'''
                return answer_part + note_block + separator

            result = re.sub(pattern, insert_note, result, count=1, flags=re.DOTALL)

    return result


def format_summary_feedback(feedback: QuizFeedback, assessment_date: str) -> str:
    """Format slimmed-down summary section for end of quiz file.

    Generates a collapsible summary section with thematic insights and
    tutor's note, designed to be appended at the end of quiz.md.

    Args:
        feedback: QuizFeedback with thematic insights and tutor's note
        assessment_date: Date string (YYYY-MM-DD)

    Returns:
        Markdown summary section with collapsible details
    """
    lines = [
        "",
        "---",
        "",
        "## Summary",
        "",
        f"**Score:** {feedback.total_score:.0f}/8 | **Assessed:** {assessment_date}",
        "",
    ]

    if feedback.thematic_insights:
        ti = feedback.thematic_insights
        wc = ti.writing_craft
        lines.extend([
            "<details>",
            "<summary>Thematic Insights</summary>",
            "",
            f"**Source Mastery:** {ti.source_mastery}",
            "",
            f"**Reasoning Quality:** {ti.reasoning_quality}",
            "",
            f"**Writing Craft:** Precision {wc.precision}/5 | Clarity {wc.clarity}/5 | Economy {wc.economy}/5",
            "",
            f"**Practice:** {wc.suggestion}",
            "</details>",
            "",
        ])

    if feedback.tutors_note:
        lines.extend([
            "<details>",
            "<summary>Tutor's Note</summary>",
            "",
            feedback.tutors_note,
            "</details>",
        ])

    return "\n".join(lines)


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

    # Build quiz answers formatted string
    quiz_answers_formatted = ""
    for qa in quiz_data['qa_pairs']:
        quiz_answers_formatted += f"**Q{qa['number']}: {qa['title']}**\n"
        quiz_answers_formatted += f"Question: {qa['question']}\n"
        quiz_answers_formatted += f"Answer: {qa['answer']}\n\n"

    # Load template and render with variables
    template = load_prompt("evaluation")
    return render_prompt(
        template,
        source_text=source_text,
        recall_points_formatted="\n".join(recall_points_formatted),
        one_sentence=recall_data['one_sentence'],
        quiz_answers_formatted=quiz_answers_formatted,
    )


def parse_inline_response(response: str) -> tuple[RecallFeedback, QuizFeedback, list[InlineAnswerFeedback]]:
    """Parse JSON from LLM evaluation response with inline feedback schema.

    Parses the new inline schema that includes errors[] with quoted_text
    anchors and writing_note for each answer.

    Args:
        response: Raw response from Claude (may include markdown code blocks)

    Returns:
        Tuple of (RecallFeedback, QuizFeedback, list[InlineAnswerFeedback])
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

    # Build QuizFeedback and InlineAnswerFeedback list
    quiz_data = data["quiz"]
    inline_feedbacks = []

    for answer in quiz_data["answers"]:
        # Parse errors for inline feedback
        errors = [
            InlineError(
                quoted_text=e["quoted_text"],
                summary=e["summary"],
                feedback=e["feedback"],
            )
            for e in answer.get("errors", [])
        ]

        inline_feedbacks.append(InlineAnswerFeedback(
            question_id=answer.get("question_id", ""),
            label=answer.get("label", ""),
            score=answer.get("score", 0),
            errors=errors,
            writing_note=answer.get("writing_note"),
        ))

    # Parse thematic insights if present
    thematic_insights = None
    if quiz_data.get("thematic_insights"):
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
        answers=[],  # Empty for inline mode - feedback is in inline_feedbacks
        total_score=quiz_data["total_score"],
        reasoning="",
        thematic_insights=thematic_insights,
        tutors_note=quiz_data.get("tutors_note"),
    )

    return recall_feedback, quiz_feedback, inline_feedbacks


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

    # Parse response using inline schema
    recall_feedback, quiz_feedback, inline_feedbacks = parse_inline_response(response_content)

    eval_date = date.today().isoformat()

    # Format and append recall feedback (unchanged from before)
    recall_md = format_recall_feedback(recall_feedback, eval_date, source_file.name)
    if "## AI Feedback" not in recall_raw:
        with open(recall_path, "a") as f:
            f.write(recall_md)

    # Handle quiz with inline feedback:
    # 1. Strip old feedback
    # 2. Inject inline annotations
    # 3. Append summary section
    # 4. Write complete file
    quiz_content = strip_feedback(quiz_raw)
    quiz_content = inject_inline_feedback(quiz_content, inline_feedbacks)
    summary_md = format_summary_feedback(quiz_feedback, eval_date)
    quiz_content = quiz_content.rstrip() + summary_md
    quiz_path.write_text(quiz_content)

    return EvaluationResult(
        recall_score=recall_feedback.score,
        quiz_score=quiz_feedback.total_score,
        recall_feedback=recall_feedback,
        quiz_feedback=quiz_feedback,
    )
