"""Template command - create human-writable templates."""
from datetime import date
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

console = Console()


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


QUIZ_ANSWERS_TEMPLATE = """<!-- TEMPLATE: Fill in your answers below -->
# Quiz Answers: Section {section_id}

> Section: {title}
> Date: {date}

---

## Recall Questions

### 1. Main Claim
[Your answer]

### 2. Mechanism
[Your answer]

### 3. Example
[Your answer]

### 4. Define: [Term 1]
[Your answer]

### 5. Define: [Term 2]
[Your answer]

---

## Explain Questions

### 6. Teach It Back
[Your answer - 3-5 sentences]

### 7. Counterfactual
[Your answer - 3-5 sentences]

---

## Apply Question

### 8. Modern Connection
[Your answer - 3-5 sentences]

---

## Score

- Recall (1-5): __ / 5
- Explain (6-7): __ / 3
- Apply (8): __ / 2
- **Total: __ / 10**
"""


def template(
    book_slug: str = typer.Argument(..., help="Book slug"),
    section_id: Optional[str] = typer.Argument(None, help="Section ID (if omitted, all sections)"),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir", help="Path to books directory"),
) -> None:
    """Create human-writable template files for sections."""

    if books_dir is None:
        books_dir = Path.cwd() / "books"

    book_dir = books_dir / book_slug
    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Book not found: {book_dir}")
        raise typer.Exit(1)

    # Load sections
    sections_path = book_dir / "sections.yaml"
    if not sections_path.exists():
        console.print("[red]Error:[/red] sections.yaml not found")
        raise typer.Exit(1)

    sections_data = yaml.safe_load(sections_path.read_text())
    sections = sections_data.get("sections", [])

    if section_id:
        sections = [s for s in sections if s["id"] == section_id]

    created_count = 0

    for section in sections:
        section_dir = book_dir / "sections" / section["id"]
        section_dir.mkdir(parents=True, exist_ok=True)

        # Create recall.md
        recall_path = section_dir / "recall.md"
        if not recall_path.exists():
            content = RECALL_TEMPLATE.format(
                section_id=section["id"],
                title=section.get("title", ""),
                date=date.today().isoformat(),
            )
            recall_path.write_text(content)
            created_count += 1

        # Create quiz-answers.md
        answers_path = section_dir / "quiz-answers.md"
        if not answers_path.exists():
            content = QUIZ_ANSWERS_TEMPLATE.format(
                section_id=section["id"],
                title=section.get("title", ""),
                date=date.today().isoformat(),
            )
            answers_path.write_text(content)
            created_count += 1

    console.print(f"[green]✓[/green] Created {created_count} template files")
