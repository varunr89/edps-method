"""Generate command - create AI content and templates for sections."""
from datetime import date
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

from edps.config import load_config
from edps.core.llm import LLMClient
from edps.core.prompts import load_prompt, render_prompt
from edps.core.ui import confirm_action

console = Console()


# Template for recall.md - human-writable memory exercise
RECALL_TEMPLATE = """<!-- TEMPLATE: Fill in sections below -->
# Recall: Section {section_id}

> Section: {title}
> Date: {date}
> Time spent: [X minutes]

---

## From Memory (before re-reading)

*Write these BEFORE looking at source or summary:*

1. [Main claim as I remember it]
2. [Key mechanism or process]
3. [Example I remember]
4. [Modern parallel that came to mind]
5. [Something I'm unsure about]

---

## After Selective Reading

*Corrections after reviewing source:*

- Correction 1: [what I got wrong or missed]
- Correction 2: [additional nuance]

---

## Self-Score

- Recall accuracy: [0-5]
- Confidence: [low / medium / high]

---

## One Sentence I'd Tell Someone

[If I had 30 seconds to explain this section, I'd say...]
"""


def generate(
    book_slug: str = typer.Argument(..., help="Book slug"),
    section_id: Optional[str] = typer.Argument(None, help="Section ID (e.g., '001'). If omitted, generates all."),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir", help="Path to books directory"),
    config_path: Optional[Path] = typer.Option(None, "--config-path", help="Path to config file"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
    gen_type: str = typer.Option("all", "--type", "-t", help="Type to generate: summary, podcast, quiz, recall, or all"),
) -> None:
    """Generate AI content for book sections."""

    # Load config
    config = load_config(config_path)

    # Setup paths
    if books_dir is None:
        books_dir = Path.cwd() / "books"

    book_dir = books_dir / book_slug
    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Book not found: {book_dir}")
        raise typer.Exit(1)

    # Load book metadata
    meta_path = book_dir / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
    else:
        meta = {"title": book_slug, "author": "Unknown"}

    # Load sections
    sections_path = book_dir / "sections.yaml"
    if not sections_path.exists():
        console.print("[red]Error:[/red] sections.yaml not found. Run 'edps ingest' first.")
        raise typer.Exit(1)

    sections_data = yaml.safe_load(sections_path.read_text())
    sections = sections_data.get("sections", [])

    # Filter to specific section if requested
    if section_id:
        sections = [s for s in sections if s["id"] == section_id]
        if not sections:
            console.print(f"[red]Error:[/red] Section not found: {section_id}")
            raise typer.Exit(1)

    # Create LLM client
    client = LLMClient(config)

    # Determine what to generate
    types_to_generate = []
    if gen_type == "all":
        types_to_generate = ["summary", "podcast", "quiz", "recall"]
    else:
        types_to_generate = [gen_type]

    # Generate for each section
    for section in sections:
        section_dir = book_dir / "sections" / section["id"]

        # Look for source file (new naming: EDPS-slug-id.txt, fallback: source.txt)
        source_filename = f"EDPS-{book_slug}-{section['id']}.txt"
        source_path = section_dir / source_filename
        if not source_path.exists():
            # Fallback to legacy source.txt
            source_path = section_dir / "source.txt"

        if not source_path.exists():
            console.print(f"[yellow]Warning:[/yellow] No source file for section {section['id']}, skipping")
            continue

        source_text = source_path.read_text(encoding="utf-8")

        for gen_type_item in types_to_generate:
            output_path = section_dir / f"{gen_type_item}.md"

            # Skip if already exists
            if output_path.exists():
                console.print(f"[dim]Skipping {section['id']}/{gen_type_item}.md (exists)[/dim]")
                continue

            # Generate
            result = _generate_content(
                client=client,
                gen_type=gen_type_item,
                section=section,
                source_text=source_text,
                meta=meta,
                section_dir=section_dir,
                skip_confirm=yes,
                book_slug=book_slug,
            )

            if result == "quit":
                raise typer.Exit(0)
            elif result == "skip":
                continue

            console.print(f"[green]✓[/green] Created {output_path}")


def _generate_content(
    client: LLMClient,
    gen_type: str,
    section: dict,
    source_text: str,
    meta: dict,
    section_dir: Path,
    skip_confirm: bool,
    book_slug: str = "",
) -> str:
    """Generate a single piece of content.

    Returns: "done", "skip", or "quit"
    """
    # Podcast is a pass-through for now (use NotebookLM with source text instead)
    if gen_type == "podcast":
        output_path = section_dir / "podcast.md"
        source_filename = f"EDPS-{book_slug}-{section['id']}.txt" if book_slug else "source.txt"
        placeholder = f"""# Podcast: Section {section['id']}

> **Use NotebookLM**: Upload the source text (`{source_filename}`) to [NotebookLM](https://notebooklm.google.com/) to generate an audio overview.

This placeholder exists to preserve the workflow structure for future podcast generation features.
"""
        output_path.write_text(placeholder, encoding="utf-8")
        console.print(f"[dim]Skipping podcast LLM call (use NotebookLM instead)[/dim]")
        return "done"

    # Recall is a human-writable template (no LLM call)
    if gen_type == "recall":
        output_path = section_dir / "recall.md"
        content = RECALL_TEMPLATE.format(
            section_id=section["id"],
            title=section.get("title", ""),
            date=date.today().isoformat(),
        )
        output_path.write_text(content, encoding="utf-8")
        console.print(f"[dim]Created recall.md template (human-writable)[/dim]")
        return "done"

    # Load and render prompt
    template = load_prompt(gen_type)

    # For podcast and quiz, we need the summary
    summary_text = ""
    if gen_type in ["podcast", "quiz"]:
        summary_path = section_dir / "summary.md"
        if summary_path.exists():
            summary_text = summary_path.read_text()

    prompt = render_prompt(
        template,
        book_title=meta.get("title", "Unknown"),
        author=meta.get("author", "Unknown"),
        section_id=section["id"],
        section_title=section.get("title", ""),
        location=section.get("location", ""),
        source_text=source_text,
        summary_text=summary_text,
        date=date.today().isoformat(),
        model=client.default_model,
    )

    # Preview
    preview = client.preview(prompt, estimated_output_tokens=1500)

    # Confirm
    if not skip_confirm:
        action = confirm_action(
            title=f"Generate {gen_type}.md",
            section=f"{section['id']}: {section.get('title', '')[:40]}",
            preview=preview,
        )

        if action == "quit":
            return "quit"
        elif action == "skip":
            return "skip"
        elif action == "view":
            console.print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
            # Re-prompt after viewing
            return _generate_content(client, gen_type, section, source_text, meta, section_dir, skip_confirm)

    # Execute
    response = client.complete(prompt)

    # Save
    output_path = section_dir / f"{gen_type}.md"
    output_path.write_text(response.content, encoding="utf-8")

    console.print(f"[dim]Tokens: {response.input_tokens} in, {response.output_tokens} out. Cost: ${response.cost:.4f}[/dim]")

    return "done"
