"""Book state detection."""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class BookState:
    """Current state of a book's processing."""
    ingested: bool
    total_sections: int
    summaries_done: int
    podcasts_done: int
    quizzes_done: int
    templates_done: int
    claims_map_done: bool
    next_section: Optional[str]
    pending_sections: List[str]


def detect_book_state(book_dir: Path) -> BookState:
    """Detect current processing state for a book.

    Args:
        book_dir: Path to book directory

    Returns:
        BookState with counts and next actions
    """
    sections_path = book_dir / "sections.yaml"

    if not sections_path.exists():
        return BookState(
            ingested=False,
            total_sections=0,
            summaries_done=0,
            podcasts_done=0,
            quizzes_done=0,
            templates_done=0,
            claims_map_done=False,
            next_section=None,
            pending_sections=[],
        )

    sections_data = yaml.safe_load(sections_path.read_text())
    sections = sections_data.get("sections", [])

    summaries_done = 0
    podcasts_done = 0
    quizzes_done = 0
    templates_done = 0
    pending = []

    for section in sections:
        section_dir = book_dir / "sections" / section["id"]

        has_summary = (section_dir / "summary.md").exists()
        has_podcast = (section_dir / "podcast.md").exists()
        has_quiz = (section_dir / "quiz.md").exists()
        has_recall = (section_dir / "recall.md").exists()

        if has_summary:
            summaries_done += 1
        if has_podcast:
            podcasts_done += 1
        if has_quiz:
            quizzes_done += 1
        if has_recall:
            templates_done += 1

        if not (has_summary and has_podcast and has_quiz):
            pending.append(section["id"])

    claims_map_done = (book_dir / "claims-map.md").exists()

    return BookState(
        ingested=True,
        total_sections=len(sections),
        summaries_done=summaries_done,
        podcasts_done=podcasts_done,
        quizzes_done=quizzes_done,
        templates_done=templates_done,
        claims_map_done=claims_map_done,
        next_section=pending[0] if pending else None,
        pending_sections=pending,
    )
