"""Ingest command - parse raw text and create sections."""
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from edps.core.chunker import find_chapter_markers, chunk_by_markers

console = Console()


def ingest(
    book_slug: str = typer.Argument(..., help="Book slug (e.g., 'wealth-of-nations')"),
    books_raw: Optional[Path] = typer.Option(
        None,
        "--books-raw",
        help="Path to books_raw directory",
    ),
    books_dir: Optional[Path] = typer.Option(
        None,
        "--books-dir",
        help="Path to books directory",
    ),
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompts",
    ),
) -> None:
    """Ingest a book from books_raw and create section structure."""

    # Default paths
    if books_raw is None:
        books_raw = Path.cwd() / "books_raw"
    if books_dir is None:
        books_dir = Path.cwd() / "books"

    # Validate slug exists in registry
    registry_path = books_dir / "_registry.yaml"
    if registry_path.exists():
        registry = yaml.safe_load(registry_path.read_text())
        registered_slugs = [b["slug"] for b in registry.get("books", [])]
        if book_slug not in registered_slugs:
            console.print(f"[red]Error:[/red] Slug '{book_slug}' not found in _registry.yaml")
            console.print(f"[dim]Available slugs: {', '.join(registered_slugs[:5])}{'...' if len(registered_slugs) > 5 else ''}[/dim]")
            console.print(f"\n[yellow]Hint:[/yellow] Add the book to _registry.yaml first:")
            console.print(f"  - slug: {book_slug}")
            console.print(f"    title: \"Your Book Title\"")
            console.print(f"    author: \"Author Name\"")
            console.print(f"    status: planned")
            raise typer.Exit(1)
    else:
        console.print(f"[yellow]Warning:[/yellow] No _registry.yaml found at {registry_path}")
        console.print("[dim]Proceeding without registry validation[/dim]")

    # Find raw text file
    raw_file = books_raw / f"{book_slug}.txt"
    if not raw_file.exists():
        # Try with .txt.utf-8 extension
        raw_file = books_raw / f"{book_slug}.txt.utf-8"

    if not raw_file.exists():
        console.print(f"[red]Error:[/red] Raw text not found: {raw_file}")
        raise typer.Exit(1)

    console.print(f"[blue]Reading:[/blue] {raw_file}")
    text = raw_file.read_text(encoding="utf-8")

    # Find chapter markers
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Finding chapter markers...", total=None)
        markers = find_chapter_markers(text)

    if not markers:
        console.print("[red]Error:[/red] No chapter markers found")
        console.print("[dim]Tried patterns: CHAPTER X, Chapter X, BOOK X, Part X, Section X[/dim]")
        raise typer.Exit(1)

    console.print(f"[green]Found {len(markers)} chapters[/green]")

    # Chunk by markers
    sections = chunk_by_markers(text, markers)

    # Show preview
    console.print()
    console.print("[bold]Proposed sections:[/bold]")
    for s in sections[:5]:
        console.print(f"  {s.id}: {s.title[:50]}... ({s.word_count:,} words)")
    if len(sections) > 5:
        console.print(f"  ... and {len(sections) - 5} more")

    # Confirm
    if not yes:
        if not typer.confirm("\nProceed with these sections?"):
            raise typer.Abort()

    # Create book directory
    book_dir = books_dir / book_slug
    book_dir.mkdir(parents=True, exist_ok=True)

    sections_dir = book_dir / "sections"
    sections_dir.mkdir(exist_ok=True)

    # Write sections.yaml
    sections_data = {
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "location": s.location,
                "start_byte": s.start_byte,
                "end_byte": s.end_byte,
                "word_count": s.word_count,
            }
            for s in sections
        ]
    }

    sections_yaml = book_dir / "sections.yaml"
    with open(sections_yaml, "w") as f:
        yaml.dump(sections_data, f, default_flow_style=False, allow_unicode=True)

    console.print(f"[green]✓[/green] Created {sections_yaml}")

    # Write source files for each section (named for easy NotebookLM upload)
    for s in sections:
        section_dir = sections_dir / s.id
        section_dir.mkdir(exist_ok=True)

        source_filename = f"EDPS-{book_slug}-{s.id}.txt"
        source_file = section_dir / source_filename
        source_file.write_text(s.text, encoding="utf-8")

    console.print(f"[green]✓[/green] Created {len(sections)} source files (EDPS-{book_slug}-XXX.txt)")

    # Create meta.yaml if it doesn't exist
    meta_path = book_dir / "meta.yaml"
    if not meta_path.exists():
        meta_data = {
            "title": book_slug.replace("-", " ").title(),
            "status": "planned",
        }
        with open(meta_path, "w") as f:
            yaml.dump(meta_data, f, default_flow_style=False)
        console.print(f"[green]✓[/green] Created {meta_path}")
