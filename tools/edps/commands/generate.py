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


# Template for one-pager.md - reader writes final distillation
ONE_PAGER_TEMPLATE = """<!-- TEMPLATE: Fill in sections below after completing all sections -->
# {book_title}: One-Pager

> Generator: 👤 Reader-written
> Author: {author}
> Completed: [YYYY-MM-DD]

---

## The Book in 10 Sentences

1. **The problem**: [What problem is the author solving?]
2. **Core claim #1**: [First major argument]
3. **Core claim #2**: [Second major argument]
4. **Core claim #3**: [Third major argument]
5. **The mechanism**: [Key process or causal chain]
6. **Best example**: [Most memorable illustration from the text]
7. **Limitation**: [What the author gets wrong or oversimplifies]
8. **Modern relevance**: [What this explains about today]
9. **Blind spot**: [What this does NOT explain]
10. **The one idea**: [What I'll remember in 10 years]

---

## Constraints

- Each sentence must contain a claim + implication (not just description)
- Sentence 7 must be critical
- Total length: 200-300 words max
"""

# Template for modern-mapping.md - reader writes contemporary connections
MODERN_MAPPING_TEMPLATE = """<!-- TEMPLATE: Fill in sections below after completing the one-pager -->
# Modern Mapping: {book_title}

> Generator: 👤 Reader-written
> Completed: [YYYY-MM-DD]

---

## Domain 1: [e.g., Technology & Labor]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 2: [e.g., Trade & Globalization]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 3: [e.g., Government & Regulation]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 4: [e.g., Inequality & Distribution]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 5: [e.g., Consumer Behavior]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

---

## Where the Book Falls Short

[What modern phenomena would surprise or confuse the author? What has changed since publication that invalidates parts of the argument?]
"""

# Template for weekly synthesis - reader copies to weekly/YYYY-MM-DD.md
WEEKLY_TEMPLATE = """<!-- TEMPLATE: Copy this file to weekly/YYYY-MM-DD.md when ready -->
# Weekly Synthesis

> Generator: 👤 Reader-written
> Week of: [YYYY-MM-DD]
> Sections covered: [001] - [00X]

---

## Top 3 Claims This Week

*What are the most important ideas from the sections you completed?*

1. **[Claim 1]**: [One sentence explanation]

2. **[Claim 2]**: [One sentence explanation]

3. **[Claim 3]**: [One sentence explanation]

---

## How They Connect

*3-5 sentences explaining how these claims relate to each other. Are they building blocks? Tensions? Different facets of one idea?*

[Your synthesis]

---

## One Strong Objection

*What's the best counterargument to what you learned this week? State it fairly — as if you believed it.*

[The objection in 2-3 sentences]

---

## My Response

*How would the author respond? How do YOU respond?*

[Your response in 2-3 sentences]

---

## Modern Connection

*One specific thing in today's world that this week's reading helps explain. Be concrete — name a company, policy, technology, or event.*

**Modern phenomenon**: [What you're connecting to]

**How this week's reading explains it**: [2-3 sentences]

---

## Gaps & Questions

*What are you still unsure about? What do you need to revisit?*

- [ ] [Question or concept to revisit]
- [ ] [Question or concept to revisit]
- [ ] [Optional third item]

---

## Interleaved Quiz Score

*If you took an interleaved quiz mixing questions from multiple sections:*

**Score**: [ ] / [ ]
**Sections with weakest recall**: [list section IDs]

---

## Time Log

| Activity | Time |
|----------|------|
| New sections completed | [X] |
| Total learning time | [X] hours |
| Synthesis writing | [X] minutes |

---

## Next Week

*What sections will you tackle? Any adjustments to your approach?*

[Your plan]
"""


def generate(
    book_slug: str = typer.Argument(..., help="Book slug"),
    section_id: Optional[str] = typer.Argument(None, help="Section ID (e.g., '001'). If omitted, generates all."),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir", help="Path to books directory"),
    config_path: Optional[Path] = typer.Option(None, "--config-path", help="Path to config file"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
    gen_type: str = typer.Option("all", "--type", "-t", help="Type: all, sections, book, summary, podcast, quiz, recall"),
) -> None:
    """Generate AI content for book sections and book-level outputs."""

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
    generate_sections = gen_type in ["all", "sections", "summary", "podcast", "quiz", "recall"]
    generate_book = gen_type in ["all", "book"]

    types_to_generate = []
    if gen_type == "all":
        types_to_generate = ["summary", "podcast", "quiz", "recall"]
    elif gen_type == "sections":
        types_to_generate = ["summary", "podcast", "quiz", "recall"]
    elif gen_type in ["summary", "podcast", "quiz", "recall"]:
        types_to_generate = [gen_type]

    # Generate for each section
    if generate_sections:
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

    # Generate book-level content
    if generate_book:
        _generate_book_content(
            client=client,
            book_dir=book_dir,
            meta=meta,
            sections=sections,
            skip_confirm=yes,
            book_slug=book_slug,
        )


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

    provider_label = f"[{response.provider.upper()}]" if hasattr(response, 'provider') else "[AZURE]"
    console.print(f"[dim]{provider_label} Tokens: {response.input_tokens} in, {response.output_tokens} out. Cost: ${response.cost:.4f}[/dim]")

    return "done"


def _write_template(path: Path, template: str, **kwargs) -> None:
    """Write a template file if it doesn't exist."""
    if path.exists():
        console.print(f"[dim]Skipping {path.name} (exists)[/dim]")
        return
    content = template.format(**kwargs) if kwargs else template
    path.write_text(content, encoding="utf-8")
    console.print(f"[green]✓[/green] Created {path.parent.name}/{path.name}")


def _generate_book_content(
    client: LLMClient,
    book_dir: Path,
    meta: dict,
    sections: list,
    skip_confirm: bool,
    book_slug: str = "",
) -> None:
    """Generate book-level outputs (templates and AI-generated)."""
    console.print("\n[bold]Generating book-level outputs...[/bold]")

    # Create directories
    outputs_dir = book_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    weekly_dir = book_dir / "weekly"
    weekly_dir.mkdir(exist_ok=True)

    book_title = meta.get("title", book_slug)
    author = meta.get("author", "Unknown")

    # Generate templates (no LLM call)
    _write_template(outputs_dir / "one-pager.md", ONE_PAGER_TEMPLATE, book_title=book_title, author=author)
    _write_template(outputs_dir / "modern-mapping.md", MODERN_MAPPING_TEMPLATE, book_title=book_title)
    _write_template(weekly_dir / "_template.md", WEEKLY_TEMPLATE)

    # Collect all summaries and quizzes
    all_summaries = []
    all_quizzes = []
    for section in sections:
        section_dir = book_dir / "sections" / section["id"]
        summary_path = section_dir / "summary.md"
        if summary_path.exists():
            all_summaries.append(f"## Section {section['id']}: {section.get('title', '')}\n\n{summary_path.read_text()}")
        quiz_path = section_dir / "quiz.md"
        if quiz_path.exists():
            all_quizzes.append(f"## Section {section['id']}: {section.get('title', '')}\n\n{quiz_path.read_text()}")

    section_ids = [s["id"] for s in sections]
    section_range = f"{section_ids[0]}-{section_ids[-1]}" if section_ids else "none"

    # Generate teachable-outline.md (AI)
    teachable_path = outputs_dir / "teachable-outline.md"
    if not teachable_path.exists() and all_summaries:
        _generate_ai_book_content(
            client=client,
            output_path=teachable_path,
            prompt_name="teachable-outline",
            meta=meta,
            all_content="\n\n---\n\n".join(all_summaries),
            content_key="all_summaries",
            section_count=len(sections),
            section_range=section_range,
            skip_confirm=skip_confirm,
        )

    # Generate question-bank.md (AI)
    qbank_path = outputs_dir / "question-bank.md"
    if not qbank_path.exists() and all_quizzes:
        _generate_ai_book_content(
            client=client,
            output_path=qbank_path,
            prompt_name="question-bank",
            meta=meta,
            all_content="\n\n---\n\n".join(all_quizzes),
            content_key="all_quizzes",
            section_count=len(sections),
            section_range=section_range,
            skip_confirm=skip_confirm,
        )


def _generate_ai_book_content(
    client: LLMClient,
    output_path: Path,
    prompt_name: str,
    meta: dict,
    all_content: str,
    content_key: str,
    section_count: int,
    section_range: str,
    skip_confirm: bool,
) -> None:
    """Generate AI book-level content."""
    template = load_prompt(prompt_name)

    prompt_vars = {
        "book_title": meta.get("title", "Unknown"),
        "author": meta.get("author", "Unknown"),
        content_key: all_content,
        "section_count": section_count,
        "section_range": section_range,
        "date": date.today().isoformat(),
        "model": client.default_model,
    }

    prompt = render_prompt(template, **prompt_vars)

    # Preview
    preview = client.preview(prompt, estimated_output_tokens=2000)

    # Confirm
    if not skip_confirm:
        action = confirm_action(
            title=f"Generate {output_path.name}",
            section="book-level",
            preview=preview,
        )
        if action in ["quit", "skip"]:
            return

    # Execute
    response = client.complete(prompt)
    output_path.write_text(response.content, encoding="utf-8")

    console.print(f"[green]✓[/green] Created {output_path.parent.name}/{output_path.name}")
    provider_label = f"[{response.provider.upper()}]" if hasattr(response, 'provider') else "[AZURE]"
    console.print(f"[dim]{provider_label} Tokens: {response.input_tokens} in, {response.output_tokens} out. Cost: ${response.cost:.4f}[/dim]")
