"""Parsers for converting markdown content to structured data."""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SummaryData:
    """Parsed summary.md content."""
    tldr: str = ""
    key_terms: list[tuple[str, str]] = field(default_factory=list)  # (term, definition)
    argument_steps: list[str] = field(default_factory=list)
    modern_application: str = ""
    source_pointers: dict = field(default_factory=dict)


def parse_summary(content: str) -> SummaryData:
    """Parse summary.md into structured data."""
    data = SummaryData()

    # TLDR
    tldr_match = re.search(r'## TLDR\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if tldr_match:
        data.tldr = tldr_match.group(1).strip()

    # Key Terms
    terms_match = re.search(r'## Key Terms\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if terms_match:
        terms_text = terms_match.group(1)
        # Match "- **term**: definition" pattern
        for match in re.finditer(r'-\s*\*\*(.+?)\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', terms_text, re.DOTALL):
            data.key_terms.append((match.group(1).strip(), match.group(2).strip()))

    # Argument Structure
    arg_match = re.search(r'## Argument Structure\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if arg_match:
        arg_text = arg_match.group(1)
        # Match numbered steps
        for match in re.finditer(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\Z)', arg_text, re.DOTALL):
            data.argument_steps.append(match.group(1).strip())

    # Modern Application
    modern_match = re.search(r'## Modern Application\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if modern_match:
        data.modern_application = modern_match.group(1).strip()

    # Source Pointers
    source_match = re.search(r'## Source Pointers\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if source_match:
        source_text = source_match.group(1)
        for match in re.finditer(r'-\s*\*\*(.+?)\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', source_text, re.DOTALL):
            data.source_pointers[match.group(1).strip()] = match.group(2).strip()

    return data


@dataclass
class RecallData:
    """Parsed recall.md content for form population."""
    memory_points: list[str] = field(default_factory=list)
    after_reading: str = ""
    score: Optional[int] = None
    confidence: Optional[str] = None
    one_sentence: str = ""
    has_feedback: bool = False


def parse_recall(content: str) -> RecallData:
    """Parse recall.md into form-compatible data."""
    data = RecallData()

    # Check for feedback
    data.has_feedback = "## AI Feedback" in content

    # Memory points (5 numbered items)
    memory_match = re.search(r'## From Memory.*?\n\n.*?\n\n((?:\d+\..*?\n)+)', content, re.DOTALL)
    if memory_match:
        points_text = memory_match.group(1)
        points = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\Z)', points_text, re.DOTALL)
        data.memory_points = [p.strip() for p in points]

    # Pad to 5 points
    while len(data.memory_points) < 5:
        data.memory_points.append("")

    # After reading
    after_match = re.search(r'## After Selective Reading\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if after_match:
        data.after_reading = after_match.group(1).strip()

    # Self-assessment score
    score_match = re.search(r'\*\*Score:\*\*\s*(\d)', content)
    if score_match:
        data.score = int(score_match.group(1))

    # Confidence
    conf_match = re.search(r'\*\*Confidence:\*\*\s*(\w+)', content)
    if conf_match:
        data.confidence = conf_match.group(1)

    # One sentence
    sentence_match = re.search(r'## One Sentence.*?\n\n(.+?)(?=\n---|\n##|\Z)', content, re.DOTALL)
    if sentence_match:
        data.one_sentence = sentence_match.group(1).strip()

    return data


@dataclass
class QuizQuestion:
    """A single quiz question."""
    number: str
    title: str
    question_type: str  # "mcq" or "prose"
    question_text: str
    options: list[str] = field(default_factory=list)  # For MCQ
    answer: str = ""
    feedback: Optional[str] = None  # Inline feedback if present


@dataclass
class QuizData:
    """Parsed quiz.md content."""
    questions: list[QuizQuestion] = field(default_factory=list)
    total_score: Optional[float] = None
    has_feedback: bool = False
    thematic_insights: Optional[str] = None
    tutors_note: Optional[str] = None


def parse_quiz(content: str) -> QuizData:
    """Parse quiz.md into form-compatible data."""
    data = QuizData()

    # Check for feedback
    data.has_feedback = "## Summary" in content or "## AI Feedback" in content

    # Extract score if present
    score_match = re.search(r'\*\*Score:\*\*\s*(\d+(?:\.\d+)?)/8', content)
    if score_match:
        data.total_score = float(score_match.group(1))

    # Parse questions
    # Pattern: ### N. Title\n\n[question]\n\n**Answer:** [answer]
    question_pattern = r'### (\d+)\.\s*(.+?)\n\n(.+?)\n\n\*\*Answer:\*\*\s*(.*?)(?=\n\n---|\n\n###|\n\n## |\Z)'

    for match in re.finditer(question_pattern, content, re.DOTALL):
        num, title, question_text, answer = match.groups()

        # Determine type: MCQ if has lettered options
        is_mcq = bool(re.search(r'\n[A-D]\)', question_text))

        q = QuizQuestion(
            number=num,
            title=title.strip(),
            question_type="mcq" if is_mcq else "prose",
            question_text=question_text.strip(),
            answer=answer.strip(),
        )

        # Extract MCQ options
        if is_mcq:
            options = re.findall(r'([A-D]\)\s*.+?)(?=\n[A-D]\)|\n\n|\Z)', question_text)
            q.options = [opt.strip() for opt in options]
            # Clean question text (remove options)
            q.question_text = re.split(r'\n[A-D]\)', question_text)[0].strip()

        data.questions.append(q)

    # Extract thematic insights
    insights_match = re.search(r'<summary>Thematic Insights</summary>\s*(.+?)</details>', content, re.DOTALL)
    if insights_match:
        data.thematic_insights = insights_match.group(1).strip()

    # Extract tutor's note
    tutor_match = re.search(r"<summary>Tutor's Note</summary>\s*(.+?)</details>", content, re.DOTALL)
    if tutor_match:
        data.tutors_note = tutor_match.group(1).strip()

    return data


def render_answer_with_highlights(answer: str) -> str:
    """Convert inline <details> feedback to hover tooltips."""
    # Pattern: text<details><summary>label</summary>feedback</details>
    pattern = r'(<details>\s*<summary>(.+?)</summary>\s*(.+?)\s*</details>)'

    def replace_with_tooltip(m):
        full_match, label, feedback = m.groups()
        # Get the text before the details tag (the error text)
        return f'<span class="error-highlight">{label}<span class="tooltip">{feedback}</span></span>'

    # This is simplified - in practice we need to find the quoted text before each details block
    result = re.sub(pattern, replace_with_tooltip, answer, flags=re.DOTALL)
    return result
