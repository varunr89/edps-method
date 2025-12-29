"""Route handlers for EDPS web UI."""
import re
from pathlib import Path
from typing import Optional

import yaml

from edps.core.state import detect_book_state


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
    """Update quiz answers in quiz.md, preserving structure and feedback."""
    section_dir = books_dir / slug / "sections" / section_id
    quiz_path = section_dir / "quiz.md"

    if not quiz_path.exists():
        return

    content = quiz_path.read_text()

    for q_key, answer in answers.items():
        # q_key is like "q1", "q2", etc.
        q_num = q_key[1:]  # Remove 'q' prefix

        # Pattern to find and replace the answer for this question
        # Matches: **Answer:** [anything until next section]
        pattern = rf'(### {q_num}\..+?\n\n\*\*Answer:\*\*\s*)(.+?)(\n\n---|\n\n###|\n\n## |\Z)'

        def replace_answer(m):
            return m.group(1) + answer + m.group(3)

        content = re.sub(pattern, replace_answer, content, flags=re.DOTALL)

    quiz_path.write_text(content)
