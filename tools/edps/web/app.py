"""FastAPI application for EDPS web UI."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from edps.web.routes import load_registry, load_book, load_section
from edps.web.parsers import parse_summary, parse_recall, parse_quiz, render_answer_with_highlights

app = FastAPI(title="EDPS Method", docs_url=None, redoc_url=None)

# Paths
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_books_dir() -> Path:
    """Get books directory from environment or default."""
    books_dir = os.environ.get("EDPS_BOOKS_DIR")
    if books_dir:
        return Path(books_dir)
    return Path.cwd() / "books"


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def index(request: Request):
    """Book list page."""
    books_dir = get_books_dir()
    books = load_registry(books_dir)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "books": books,
    })


@app.get("/book/{slug}")
async def book_detail(request: Request, slug: str):
    """Book detail page with section list."""
    books_dir = get_books_dir()
    book = load_book(books_dir, slug)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return templates.TemplateResponse("book.html", {
        "request": request,
        "book": book,
    })


@app.get("/book/{slug}/{section_id}")
async def section_workspace(request: Request, slug: str, section_id: str, tab: str = "summary"):
    """Section workspace with tabs."""
    books_dir = get_books_dir()
    section = load_section(books_dir, slug, section_id)

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    # Default to summary tab, or first available
    if tab not in ["summary", "recall", "quiz", "podcast"]:
        tab = "summary"

    return templates.TemplateResponse("section.html", {
        "request": request,
        "section": section,
        "tab": tab,
        "parse_summary": parse_summary,
        "parse_recall": parse_recall,
        "parse_quiz": parse_quiz,
        "render_highlights": render_answer_with_highlights,
    })
