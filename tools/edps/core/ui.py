"""Terminal UI components."""
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from edps.core.llm import LLMPreview


console = Console()


def format_preview_panel(
    title: str,
    section: str,
    preview: LLMPreview,
) -> Panel:
    """Format a preview panel for confirmation.

    Args:
        title: Action being performed
        section: Section identifier
        preview: LLM call preview

    Returns:
        Rich Panel for display
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")

    table.add_row("Action", title)
    table.add_row("Section", section)
    table.add_row("Model", preview.model)
    table.add_row("Input tokens", f"{preview.input_tokens:,}")
    table.add_row("Est. output", f"{preview.estimated_output_tokens:,}")
    table.add_row("Est. cost", f"${preview.estimated_cost:.4f}")

    return Panel(table, title=section, border_style="blue")


def confirm_action(
    title: str,
    section: str,
    preview: LLMPreview,
    skip_confirm: bool = False,
) -> str:
    """Show preview and get user confirmation.

    Args:
        title: Action being performed
        section: Section identifier
        preview: LLM call preview
        skip_confirm: If True, auto-proceed

    Returns:
        One of: "proceed", "skip", "view", "quit"
    """
    if skip_confirm:
        return "proceed"

    panel = format_preview_panel(title, section, preview)
    console.print(panel)
    console.print()
    console.print("[dim][Enter] Proceed  [s] Skip  [v] View prompt  [q] Quit[/dim]")

    while True:
        choice = console.input("> ").strip().lower()

        if choice == "" or choice == "p" or choice == "proceed":
            return "proceed"
        elif choice == "s" or choice == "skip":
            return "skip"
        elif choice == "v" or choice == "view":
            return "view"
        elif choice == "q" or choice == "quit":
            return "quit"
        else:
            console.print("[red]Invalid choice. Try again.[/red]")
