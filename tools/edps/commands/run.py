"""Run command - launches web UI server."""
from pathlib import Path
from typing import Optional
import webbrowser

import typer
import uvicorn
from rich.console import Console

console = Console()


def run(
    book_slug: Optional[str] = typer.Argument(None, help="Book slug (opens directly to book)"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to run on"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't auto-open browser"),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir"),
) -> None:
    """Launch the EDPS web UI."""
    import os

    # Set books directory for the app to find
    if books_dir is None:
        books_dir = Path.cwd() / "books"
    os.environ["EDPS_BOOKS_DIR"] = str(books_dir.absolute())

    url = f"http://localhost:{port}"
    if book_slug:
        url = f"{url}/book/{book_slug}"

    console.print(f"[bold green]Starting EDPS web UI...[/bold green]")
    console.print(f"[dim]Open {url} in your browser[/dim]")

    if not no_browser:
        # Open browser after slight delay to let server start
        import threading
        def open_browser():
            import time
            time.sleep(1)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    # Run uvicorn
    uvicorn.run(
        "edps.web.app:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="warning",
    )
