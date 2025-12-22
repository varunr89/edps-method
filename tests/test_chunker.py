"""Tests for text chunking."""
from edps.core.chunker import find_chapter_markers


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
