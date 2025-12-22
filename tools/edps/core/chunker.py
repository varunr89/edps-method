"""Text chunking utilities."""
import re
from dataclasses import dataclass
from typing import List, Optional


def _parse_chapter_number(num_str: str) -> int:
    """Convert chapter number (Roman or Arabic) to integer."""
    # Try Arabic first
    if num_str.isdigit():
        return int(num_str)

    # Roman numeral conversion
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    prev = 0
    for char in reversed(num_str.upper()):
        val = roman_map.get(char, 0)
        if val < prev:
            result -= val
        else:
            result += val
        prev = val
    return result


@dataclass
class ChapterMarker:
    """A detected chapter/section marker."""
    number: str
    title: str
    start_pos: int


@dataclass
class Section:
    """A chunked section of text."""
    id: str
    title: str
    location: str
    start_byte: int
    end_byte: int
    word_count: int
    text: str


# Patterns to try in order
CHAPTER_PATTERNS = [
    # CHAPTER I. or CHAPTER 1.
    r'^CHAPTER\s+([IVXLCDM]+|\d+)\.?\s*\n+([A-Z][^\n]+)',
    # Chapter 1: Title
    r'^Chapter\s+(\d+):\s*([^\n]+)',
    # BOOK I or Book I
    r'^BOOK\s+([IVXLCDM]+|\d+)\.?\s*\n+([A-Z][^\n]+)',
    # Part I or PART I
    r'^(?:PART|Part)\s+([IVXLCDM]+|\d+)\.?\s*\n+([A-Z][^\n]+)',
    # Section 1 or § 1
    r'^(?:Section|§)\s*(\d+)\.?\s*([^\n]*)',
]


def find_chapter_markers(text: str) -> List[dict]:
    """Find chapter/section markers in text using regex.

    Args:
        text: Full book text

    Returns:
        List of dicts with 'number', 'title', 'start_pos'
    """
    markers = []

    for pattern in CHAPTER_PATTERNS:
        for match in re.finditer(pattern, text, re.MULTILINE):
            number = match.group(1).strip()
            title = match.group(2).strip() if match.lastindex >= 2 else ""

            # Clean up title (remove trailing punctuation)
            title = re.sub(r'[.\s]+$', '', title)

            markers.append({
                "number": number,
                "title": title,
                "start_pos": match.start(),
            })

        # If we found markers with this pattern, stop trying others
        if markers:
            break

    # Sort by position
    markers.sort(key=lambda m: m["start_pos"])

    return markers


def chunk_by_markers(
    text: str,
    markers: List[dict],
    target_words: int = 2500,
    min_words: int = 1500,
    max_words: int = 4000,
) -> List[Section]:
    """Chunk text into sections based on markers.

    Args:
        text: Full book text
        markers: Chapter markers from find_chapter_markers
        target_words: Target words per section
        min_words: Minimum words per section (merge if smaller)
        max_words: Maximum words per section (split if larger)

    Returns:
        List of Section objects
    """
    if not markers:
        return []

    sections = []
    section_num = 1
    book_num = 1
    prev_chapter_int = 0

    for i, marker in enumerate(markers):
        start = marker["start_pos"]

        # End is either next marker or end of text
        if i + 1 < len(markers):
            end = markers[i + 1]["start_pos"]
        else:
            end = len(text)

        section_text = text[start:end]
        word_count = len(section_text.split())

        # Detect book boundary: chapter number reset (e.g., XI -> I)
        chapter_int = _parse_chapter_number(marker["number"])
        if chapter_int <= prev_chapter_int and i > 0:
            book_num += 1
        prev_chapter_int = chapter_int

        section = Section(
            id=f"{section_num:03d}",
            title=marker["title"],
            location=f"Book {book_num}, Chapter {marker['number']}",
            start_byte=start,
            end_byte=end,
            word_count=word_count,
            text=section_text,
        )

        sections.append(section)
        section_num += 1

    return sections
