"""Tests for text chunking."""
from edps.core.chunker import find_chapter_markers, chunk_by_markers


def test_find_chapter_markers_standard():
    """Detects 'CHAPTER X' format."""
    text = """
CHAPTER I.
OF THE DIVISION OF LABOUR.

The greatest improvement in the productive powers...

CHAPTER II.
OF THE PRINCIPLE WHICH GIVES OCCASION TO THE DIVISION OF LABOUR.

This division of labour...

CHAPTER III.
THAT THE DIVISION OF LABOUR IS LIMITED BY THE EXTENT OF THE MARKET.

As it is the power...
"""

    markers = find_chapter_markers(text)

    assert len(markers) == 3
    assert markers[0]["title"] == "OF THE DIVISION OF LABOUR"
    assert markers[1]["title"] == "OF THE PRINCIPLE WHICH GIVES OCCASION TO THE DIVISION OF LABOUR"


def test_chunk_by_markers():
    """chunk_by_markers creates Section objects."""
    text = """
CHAPTER I.
OF THE DIVISION OF LABOUR.

The greatest improvement in the productive powers of labour...
This is the first chapter content with many words.

CHAPTER II.
OF THE PRINCIPLE WHICH GIVES OCCASION TO THE DIVISION OF LABOUR.

This division of labour, from which so many advantages are derived...
Second chapter content here.
"""

    markers = find_chapter_markers(text)
    sections = chunk_by_markers(text, markers)

    assert len(sections) == 2
    assert sections[0].id == "001"
    assert sections[0].title == "OF THE DIVISION OF LABOUR"
    assert sections[0].location == "Book 1, Chapter I"
    assert sections[0].word_count > 0
    assert "greatest improvement" in sections[0].text
