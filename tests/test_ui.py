"""Tests for UI components."""
from io import StringIO

from rich.console import Console

from edps.core.llm import LLMPreview
from edps.core.ui import format_preview_panel


def test_format_preview_panel():
    """Preview panel shows key information."""
    preview = LLMPreview(
        prompt="Test prompt...",
        input_tokens=1500,
        estimated_output_tokens=500,
        estimated_cost=0.012,
        model="claude-sonnet-4-20250514",
    )

    output = StringIO()
    console = Console(file=output, force_terminal=True)

    panel = format_preview_panel(
        title="Generate summary.md",
        section="001: Division of Labor",
        preview=preview,
    )
    console.print(panel)

    result = output.getvalue()
    assert "1,500" in result or "1500" in result  # Input tokens
    assert "500" in result  # Output tokens
    assert "0.01" in result  # Cost (formatted)
