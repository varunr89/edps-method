"""Eval command - AI evaluation of homework."""
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from edps.config import load_config
from edps.evaluation import evaluate_section
from edps.progress import update_progress, SectionStatus

console = Console()

def eval_cmd(
    book_slug: str = typer.Argument(..., help="Book slug (e.g., 'wealth-of-nations')"),
    section_id: str = typer.Argument(..., help="Section ID (e.g., '001')"),
    books_dir: Optional[Path] = typer.Option(None, help="Path to books directory"),
) -> None:
    """Evaluate recall and quiz answers using AI."""
    if books_dir is None:
        books_dir = Path.cwd() / "books"
    section_path = books_dir / book_slug / "sections" / section_id
    if not section_path.exists():
        console.print(f"[red]Error:[/red] Section not found: {section_path}")
        raise typer.Exit(1)
    console.print(f"Evaluating {book_slug}/{section_id}...")
    try:
        config = load_config()
        result = evaluate_section(section_path, book_slug, section_id, config)
        book_path = books_dir / book_slug
        update_progress(book_path, {
            section_id: SectionStatus(is_complete=True, recall_score=result.recall_score, quiz_score=result.quiz_score)
        })
        console.print(f"\n[green]✓[/green] Evaluation complete!")
        console.print(f"  Recall: {result.recall_score}/5")
        console.print(f"  Quiz: {result.quiz_score}/8")
        console.print(f"\nFeedback appended to recall.md and quiz.md")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Evaluation failed: {e}")
        raise typer.Exit(1)
