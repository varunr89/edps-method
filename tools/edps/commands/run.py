"""Run command - interactive workflow runner."""
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from edps.config import load_config
from edps.core.state import detect_book_state
from edps.commands.generate import generate

console = Console()


def run(
    book_slug: str = typer.Argument(..., help="Book slug"),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir"),
    config_path: Optional[Path] = typer.Option(None, "--config-path"),
) -> None:
    """Interactive workflow runner for EDPS Method."""

    if books_dir is None:
        books_dir = Path.cwd() / "books"

    book_dir = books_dir / book_slug
    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Book not found: {book_dir}")
        raise typer.Exit(1)

    # Load metadata
    meta_path = book_dir / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
    else:
        meta = {"title": book_slug}

    while True:
        # Detect state
        state = detect_book_state(book_dir)

        # Show header
        console.clear()
        console.print(Panel(
            f"[bold]{meta.get('title', book_slug)}[/bold]\n"
            f"{meta.get('author', 'Unknown')}, {meta.get('year', '')}\n\n"
            f"Status: {state.total_sections} sections, "
            f"{state.summaries_done} summaries, "
            f"{state.podcasts_done} podcasts, "
            f"{state.quizzes_done} quizzes",
            title="EDPS Method",
            border_style="blue",
        ))

        # Build menu options
        options = []

        if not state.ingested:
            console.print("\n[yellow]Book not ingested. Run 'edps ingest' first.[/yellow]")
            break

        if state.pending_sections:
            options.append(f"[1] Continue generating ({len(state.pending_sections)} pending)")

        if state.summaries_done > 0:
            options.append("[2] Review existing outputs")

        options.append("[3] Regenerate a specific section")

        if state.summaries_done > 0:
            options.append("[4] Generate recall templates (recall.md)")

        options.append("[5] View cost summary")
        options.append("[q] Quit")

        console.print("\nWhat would you like to do?\n")
        for opt in options:
            console.print(f"  {opt}")

        choice = Prompt.ask("\n>", default="1")

        if choice == "q" or choice == "quit":
            break
        elif choice == "1" and state.pending_sections:
            # Continue generating
            generate(
                book_slug=book_slug,
                section_id=None,
                books_dir=books_dir,
                config_path=config_path,
                yes=False,
                gen_type="all",
            )
        elif choice == "3":
            section_id = Prompt.ask("Section ID")
            gen_type = Prompt.ask("Type (summary/podcast/quiz/all)", default="all")
            generate(
                book_slug=book_slug,
                section_id=section_id,
                books_dir=books_dir,
                config_path=config_path,
                yes=False,
                gen_type=gen_type,
            )
        elif choice == "4":
            generate(
                book_slug=book_slug,
                section_id=None,
                books_dir=books_dir,
                config_path=config_path,
                yes=True,
                gen_type="recall",
            )
        elif choice == "5":
            console.print("\n[dim]Cost tracking not yet implemented[/dim]")
            Prompt.ask("Press Enter to continue")

        # Pause before loop
        if choice not in ["q", "quit"]:
            Prompt.ask("\nPress Enter to continue")
