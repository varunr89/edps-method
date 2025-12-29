"""Route handlers for EDPS web UI."""
import re
from pathlib import Path
from typing import Optional

import yaml

from edps.core.state import detect_book_state

# Compiled patterns for quiz answer parsing (state machine approach)
_QUESTION_HEADER_RE = re.compile(r"^###\s+(\d+)\.")
_SECTION_HEADER_RE = re.compile(r"^##\s+")
_ANSWER_MARK = "**Answer:**"


def load_registry(books_dir: Path) -> list[dict]:
    """Load book registry with state info."""
    registry_path = books_dir / "_registry.yaml"
    if not registry_path.exists():
        return []

    data = yaml.safe_load(registry_path.read_text())
    books = data.get("books", [])

    # Enrich with state info
    for book in books:
        book_dir = books_dir / book["slug"]
        if book_dir.exists():
            state = detect_book_state(book_dir)
            book["state"] = {
                "total_sections": state.total_sections,
                "completed": state.total_sections - len(state.pending_sections),
                "has_content": state.ingested,
            }
        else:
            book["state"] = {
                "total_sections": 0,
                "completed": 0,
                "has_content": False,
            }

    return books


def load_book(books_dir: Path, slug: str) -> Optional[dict]:
    """Load a single book with full details."""
    registry = load_registry(books_dir)
    book = next((b for b in registry if b["slug"] == slug), None)
    if not book:
        return None

    book_dir = books_dir / slug

    # Load sections from sections.yaml
    sections_path = book_dir / "sections.yaml"
    if sections_path.exists():
        sections_data = yaml.safe_load(sections_path.read_text())
        sections = sections_data.get("sections", [])

        # Enrich sections with file existence info
        for section in sections:
            section_dir = book_dir / "sections" / section["id"]
            section["files"] = {
                "summary": (section_dir / "summary.md").exists(),
                "recall": (section_dir / "recall.md").exists(),
                "quiz": (section_dir / "quiz.md").exists(),
                "podcast": (section_dir / "podcast.md").exists(),
            }
            # Check if quiz has been evaluated (has feedback)
            quiz_path = section_dir / "quiz.md"
            if quiz_path.exists():
                content = quiz_path.read_text()
                section["has_feedback"] = "## Summary" in content or "## AI Feedback" in content
            else:
                section["has_feedback"] = False

        book["sections"] = sections
    else:
        book["sections"] = []

    return book


def load_section(books_dir: Path, slug: str, section_id: str) -> Optional[dict]:
    """Load a section with all its content."""
    book = load_book(books_dir, slug)
    if not book:
        return None

    section = next((s for s in book.get("sections", []) if s["id"] == section_id), None)
    if not section:
        return None

    section_dir = books_dir / slug / "sections" / section_id

    # Load file contents
    for file_type in ["summary", "recall", "quiz", "podcast"]:
        file_path = section_dir / f"{file_type}.md"
        if file_path.exists():
            section[f"{file_type}_content"] = file_path.read_text()
        else:
            section[f"{file_type}_content"] = None

    section["book"] = book
    return section


def write_recall(
    books_dir: Path,
    slug: str,
    section_id: str,
    memory_points: list[str],
    after_reading: str,
    score: Optional[int],
    confidence: Optional[str],
    one_sentence: str,
) -> None:
    """Write recall data to recall.md, preserving feedback if present."""
    section_dir = books_dir / slug / "sections" / section_id
    recall_path = section_dir / "recall.md"

    # Read existing content to preserve feedback
    existing_feedback = ""
    if recall_path.exists():
        content = recall_path.read_text()
        feedback_match = re.search(r'(---\s*\n\n## AI Feedback.*)', content, re.DOTALL)
        if feedback_match:
            existing_feedback = feedback_match.group(1)

    # Build new content
    lines = [
        f"# Recall: Section {section_id}",
        "",
        "## From Memory",
        "",
        "*Write 5 key points from memory before re-reading.*",
        "",
    ]

    for i, point in enumerate(memory_points):
        lines.append(f"{i+1}. {point}")

    lines.extend([
        "",
        "## After Selective Reading",
        "",
        after_reading,
        "",
        "## Self-Assessment",
        "",
        f"**Score:** {score if score is not None else '_'}/5",
        f"**Confidence:** {confidence or '_'}",
        "",
        "## One Sentence Summary",
        "",
        one_sentence,
    ])

    if existing_feedback:
        lines.append("")
        lines.append(existing_feedback)

    recall_path.write_text("\n".join(lines))


def update_quiz_answers(books_dir: Path, slug: str, section_id: str, answers: dict[str, str]) -> None:
    """Update quiz answers in quiz.md using line-by-line state machine.

    This approach is more robust than regex because it:
    - Handles empty answers (clearing)
    - Handles multi-line answers
    - Won't truncate if answer contains '---' or '###'
    - Processes markdown as structural blocks, not pattern matches
    """
    section_dir = books_dir / slug / "sections" / section_id
    quiz_path = section_dir / "quiz.md"

    if not quiz_path.exists():
        return

    content = quiz_path.read_text()
    lines = content.splitlines()

    # Normalize keys like {"q1": "..."} -> {"1": "..."}
    answers_by_num = {k[1:]: v for k, v in answers.items() if k.startswith("q")}

    out: list[str] = []
    i = 0
    while i < len(lines):
        m = _QUESTION_HEADER_RE.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue

        q_num = m.group(1)

        # Find end of this question block (next question or next section)
        j = i + 1
        while j < len(lines):
            if _QUESTION_HEADER_RE.match(lines[j]) or _SECTION_HEADER_RE.match(lines[j]):
                break
            j += 1

        block = lines[i:j]
        if q_num in answers_by_num:
            block = _replace_answer_in_block(block, answers_by_num[q_num])

        out.extend(block)
        i = j

    quiz_path.write_text("\n".join(out))


def _replace_answer_in_block(block_lines: list[str], new_answer: str) -> list[str]:
    """Find **Answer:** line in block and replace answer content."""
    for idx, line in enumerate(block_lines):
        if _ANSWER_MARK in line:
            return _splice_answer(block_lines, idx, new_answer)
    return block_lines


def _splice_answer(block_lines: list[str], answer_idx: int, new_answer: str) -> list[str]:
    """Replace answer content starting at answer_idx line."""
    end = len(block_lines)

    # Find where the answer should end (blank line before a structural boundary)
    k = answer_idx + 1
    while k < len(block_lines):
        if block_lines[k].strip() == "" and _next_nonempty_is_boundary(block_lines, k + 1):
            end = k
            break
        if _is_boundary_start(block_lines, k):
            # Keep the blank line before a boundary if present
            end = k - 1 if k > answer_idx + 1 and block_lines[k - 1].strip() == "" else k
            break
        k += 1

    prefix = block_lines[:answer_idx]
    suffix = block_lines[end:]

    marker_line = block_lines[answer_idx]
    marker_pos = marker_line.find(_ANSWER_MARK)
    if marker_pos == -1:
        return block_lines

    marker_prefix = marker_line[: marker_pos + len(_ANSWER_MARK)]

    answer_lines = new_answer.splitlines()
    if not answer_lines:
        new_answer_block = [marker_prefix]
    else:
        first = answer_lines[0]
        new_answer_block = [marker_prefix + (" " + first if first else "")]
        if len(answer_lines) > 1:
            new_answer_block.extend(answer_lines[1:])

    return prefix + new_answer_block + suffix


def _is_boundary_start(lines: list[str], idx: int) -> bool:
    """Check if line at idx is a structural boundary."""
    line = lines[idx]
    if _QUESTION_HEADER_RE.match(line) or _SECTION_HEADER_RE.match(line):
        return True
    if line.strip() == "---":
        # Treat '---' as a boundary only if a header follows
        j = idx + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j < len(lines) and (
            _QUESTION_HEADER_RE.match(lines[j]) or _SECTION_HEADER_RE.match(lines[j])
        ):
            return True
    return False


def _next_nonempty_is_boundary(lines: list[str], start: int) -> bool:
    """Check if next non-empty line is a structural boundary."""
    j = start
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j >= len(lines):
        return False
    return _is_boundary_start(lines, j)
