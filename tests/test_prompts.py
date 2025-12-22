"""Tests for prompt templates."""
from edps.core.prompts import load_prompt, render_prompt


def test_load_prompt_summary():
    """Can load summary prompt template."""
    template = load_prompt("summary")

    assert "{book_title}" in template
    assert "{source_text}" in template
    assert "TLDR" in template


def test_render_prompt():
    """render_prompt substitutes variables."""
    template = "Hello {name}, your book is {book_title}."

    result = render_prompt(template, name="Alice", book_title="Test Book")

    assert result == "Hello Alice, your book is Test Book."
