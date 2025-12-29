"""FastAPI application for EDPS web UI."""
import os
from pathlib import Path

from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from edps.web.routes import load_registry, load_book, load_section, write_recall, update_quiz_answers
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


@app.post("/book/{slug}/{section_id}/save/recall")
async def save_recall(
    slug: str,
    section_id: str,
    memory_0: str = Form(""),
    memory_1: str = Form(""),
    memory_2: str = Form(""),
    memory_3: str = Form(""),
    memory_4: str = Form(""),
    after_reading: str = Form(""),
    score: Optional[int] = Form(None),
    confidence: Optional[str] = Form(None),
    one_sentence: str = Form(""),
):
    """Save recall form data to recall.md."""
    books_dir = get_books_dir()
    write_recall(
        books_dir, slug, section_id,
        memory_points=[memory_0, memory_1, memory_2, memory_3, memory_4],
        after_reading=after_reading,
        score=score,
        confidence=confidence,
        one_sentence=one_sentence,
    )

    return HTMLResponse("Saved &#10003;")


@app.post("/book/{slug}/{section_id}/save/quiz")
async def save_quiz(slug: str, section_id: str, request: Request):
    """Save quiz answers to quiz.md."""
    form_data = await request.form()
    answers = {k: v for k, v in form_data.items() if k.startswith('q')}

    books_dir = get_books_dir()
    update_quiz_answers(books_dir, slug, section_id, answers)

    return HTMLResponse("Saved &#10003;")


@app.post("/book/{slug}/{section_id}/evaluate/recall")
async def evaluate_recall_endpoint(slug: str, section_id: str):
    """Trigger AI evaluation of recall answers."""
    from edps.evaluation import evaluate_section
    from edps.config import load_config

    books_dir = get_books_dir()
    section_dir = books_dir / slug / "sections" / section_id

    try:
        config = load_config()
        result = evaluate_section(section_dir, slug, section_id, config)

        # Return feedback summary HTML
        html = f"""
        <div class="card bg-surface p-6 rounded-lg border-l-4 border-success">
            <h3 class="text-lg font-semibold mb-4">Recall Feedback</h3>
            <p class="font-mono text-xl mb-4">Score: {result.recall_score}/5</p>
            <p class="text-muted">{result.recall_feedback.reasoning}</p>
        </div>
        """
        return HTMLResponse(html)

    except Exception as e:
        return HTMLResponse(f"""
        <div class="card bg-surface p-6 rounded-lg border-l-4 border-error">
            <h3 class="text-lg font-semibold mb-2 text-error">Evaluation Error</h3>
            <p class="text-sm">{str(e)}</p>
        </div>
        """)


@app.post("/book/{slug}/{section_id}/evaluate/quiz")
async def evaluate_quiz_endpoint(slug: str, section_id: str):
    """Trigger AI evaluation of quiz answers."""
    from edps.evaluation import evaluate_section
    from edps.config import load_config

    books_dir = get_books_dir()
    section_dir = books_dir / slug / "sections" / section_id

    try:
        config = load_config()
        result = evaluate_section(section_dir, slug, section_id, config)

        # Build feedback HTML
        insights_html = ""
        if result.quiz_feedback.thematic_insights:
            ti = result.quiz_feedback.thematic_insights
            insights_html = f"""
            <details class="mb-4">
                <summary class="text-muted cursor-pointer">Thematic Insights</summary>
                <div class="mt-2 text-sm">
                    <p><strong>Source Mastery:</strong> {ti.source_mastery}</p>
                    <p><strong>Reasoning:</strong> {ti.reasoning_quality}</p>
                    <p><strong>Writing:</strong> Precision {ti.writing_craft.precision}/5,
                       Clarity {ti.writing_craft.clarity}/5, Economy {ti.writing_craft.economy}/5</p>
                </div>
            </details>
            """

        tutor_html = ""
        if result.quiz_feedback.tutors_note:
            tutor_html = f"""
            <details>
                <summary class="text-muted cursor-pointer">Tutor's Note</summary>
                <div class="mt-2 text-sm italic">{result.quiz_feedback.tutors_note}</div>
            </details>
            """

        html = f"""
        <div class="card bg-surface p-6 rounded-lg border-l-4 border-accent">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold">Quiz Feedback</h3>
                <span class="font-mono text-xl">{result.quiz_score}/8</span>
            </div>
            {insights_html}
            {tutor_html}
            <p class="text-sm text-muted mt-4">Reload the page to see inline feedback on your answers.</p>
        </div>
        """
        return HTMLResponse(html)

    except Exception as e:
        return HTMLResponse(f"""
        <div class="card bg-surface p-6 rounded-lg border-l-4 border-error">
            <h3 class="text-lg font-semibold mb-2 text-error">Evaluation Error</h3>
            <p class="text-sm">{str(e)}</p>
        </div>
        """)
