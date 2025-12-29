"""FastAPI application for EDPS web UI."""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from edps.web.routes import load_registry, load_book, load_section

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
