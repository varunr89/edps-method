"""Sync command - manually update progress from homework files."""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from edps.progress import (
    check_section_completion,
    update_progress,
)

console = Console()


def sync(
    book_slug: Optional[str] = typer.Argument(
        None,
        help="Book slug to sync (e.g., 'wealth-of-nations'). Omit for --all.",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Rescan all sections (not just recent changes)",
    ),
    all_books: bool = typer.Option(
        False,
        "--all",
        help="Sync all books",
    ),
    books_dir: Optional[Path] = typer.Option(
        None,
        "--books-dir",
        help="Path to books directory",
    ),
) -> None:
    """Sync progress.yaml from homework files."""
    if books_dir is None:
        books_dir = Path.cwd() / "books"

    if not books_dir.exists():
        console.print(f"[red]Error:[/red] Books directory not found: {books_dir}")
        raise typer.Exit(1)

    # Determine which books to sync
    if all_books:
        book_slugs = [
            d.name for d in books_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]
    elif book_slug:
        book_slugs = [book_slug]
    else:
        console.print("[red]Error:[/red] Specify a book slug or use --all")
        raise typer.Exit(1)

    for slug in book_slugs:
        book_path = books_dir / slug
        sections_path = book_path / "sections"

        if not sections_path.exists():
            console.print(f"[yellow]Skipping {slug}:[/yellow] No sections directory")
            continue

        console.print(f"[blue]Syncing:[/blue] {slug}")

        # Check all sections
        section_updates = {}
        for section_dir in sorted(sections_path.iterdir()):
            if section_dir.is_dir():
                status = check_section_completion(section_dir)
                section_updates[section_dir.name] = status

                if status.is_complete:
                    console.print(f"  [green]✓[/green] {section_dir.name}")
                else:
                    console.print(f"  [dim]○[/dim] {section_dir.name}")

        # Update progress
        update_progress(book_path, section_updates)

        completed = sum(1 for s in section_updates.values() if s.is_complete)
        console.print(
            f"[green]Done:[/green] {completed}/{len(section_updates)} sections complete"
        )
