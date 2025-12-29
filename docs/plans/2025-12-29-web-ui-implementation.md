# Web UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local web server (`edps run`) that provides a browser-based UI for reading summaries, writing recall notes, answering quizzes, and receiving AI feedback.

**Architecture:** FastAPI backend serving server-rendered HTML with Jinja2 templates. HTMX provides interactivity (auto-save, feedback loading) without client-side JavaScript frameworks. Tailwind CSS from CDN for styling.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Jinja2, HTMX, Tailwind CSS

---

## Prerequisites

Install new dependencies in the existing virtual environment:

```bash
cd tools
source .venv/bin/activate
pip install fastapi uvicorn jinja2 python-multipart
```

---

## Task 1: Create Web Module Structure

**Files:**
- Create: `tools/edps/web/__init__.py`
- Create: `tools/edps/web/app.py`

**Step 1: Create web package**

```python
# tools/edps/web/__init__.py
"""EDPS Web UI package."""
```

**Step 2: Create minimal FastAPI app**

```python
# tools/edps/web/app.py
"""FastAPI application for EDPS web UI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="EDPS Method", docs_url=None, redoc_url=None)

# Static files will be mounted after templates are set up
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

**Step 3: Test manually**

```bash
cd tools
PYTHONPATH="$PWD" python -c "from edps.web.app import app; print('Import OK')"
```

Expected: No errors, prints "Import OK"

**Step 4: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): create web module with minimal FastAPI app"
```

---

## Task 2: Update CLI Run Command

**Files:**
- Modify: `tools/edps/commands/run.py`

**Step 1: Replace terminal UI with web server launch**

```python
# tools/edps/commands/run.py
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
```

**Step 2: Test command runs**

```bash
cd /Users/varunr/projects/edps-method
PYTHONPATH="$PWD/tools" python -m edps.cli run --no-browser --help
```

Expected: Shows help text with new options

**Step 3: Commit**

```bash
git add tools/edps/commands/run.py
git commit -m "feat(cli): update run command to launch web server"
```

---

## Task 3: Create Base Template with Styling

**Files:**
- Create: `tools/edps/web/templates/base.html`
- Create: `tools/edps/web/static/styles.css`

**Step 1: Create templates directory**

```bash
mkdir -p tools/edps/web/templates tools/edps/web/static
```

**Step 2: Create base template**

```html
<!-- tools/edps/web/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}EDPS Method{% endblock %}</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        cream: '#FAF8F5',
                        surface: '#FFFFFF',
                        text: '#3D3229',
                        muted: '#8B7355',
                        accent: '#B8860B',
                        success: '#5B7C5B',
                        error: '#A65D57',
                    },
                    fontFamily: {
                        serif: ['Crimson Pro', 'Georgia', 'serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    },
                }
            }
        }
    </script>

    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Custom styles -->
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="bg-cream text-text font-serif min-h-screen">
    <div class="max-w-4xl mx-auto px-6 py-8">
        {% block content %}{% endblock %}
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
```

**Step 3: Create custom styles**

```css
/* tools/edps/web/static/styles.css */

/* Paper texture background */
body {
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    background-blend-mode: soft-light;
    background-size: 200px 200px;
}

/* Warm shadows */
.card {
    box-shadow: 0 4px 6px -1px rgba(61, 50, 41, 0.1),
                0 2px 4px -1px rgba(61, 50, 41, 0.06);
}

/* Tab styling */
.tab {
    border-bottom: 2px solid transparent;
    transition: border-color 0.2s ease;
}

.tab.active {
    border-color: #B8860B;
}

.tab:hover:not(.active) {
    border-color: #8B7355;
}

/* Error highlight (wavy underline) */
.error-highlight {
    text-decoration: underline wavy #A65D57;
    text-decoration-skip-ink: none;
    cursor: help;
    position: relative;
}

/* Tooltip */
.tooltip {
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: #3D3229;
    color: #FAF8F5;
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    font-size: 0.875rem;
    max-width: 300px;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.2s ease, visibility 0.2s ease;
    z-index: 50;
}

.error-highlight:hover .tooltip {
    opacity: 1;
    visibility: visible;
}

/* Form inputs */
textarea, input[type="text"] {
    font-family: 'Crimson Pro', Georgia, serif;
    font-size: 1.1rem;
    line-height: 1.6;
}

textarea:focus, input:focus {
    outline: none;
    border-color: #B8860B;
    box-shadow: 0 0 0 2px rgba(184, 134, 11, 0.2);
}

/* Save indicator */
.save-indicator {
    font-size: 0.875rem;
    color: #5B7C5B;
    transition: opacity 0.3s ease;
}

/* Gold accent divider */
.divider-gold {
    border-top: 1px solid #B8860B;
    opacity: 0.3;
}

/* Progress bar */
.progress-bar {
    background: linear-gradient(to right, #B8860B, #D4A84B);
}

/* Collapsible sections */
details summary {
    cursor: pointer;
    font-weight: 500;
}

details summary::-webkit-details-marker {
    display: none;
}

details summary::before {
    content: '▸ ';
    color: #8B7355;
}

details[open] summary::before {
    content: '▾ ';
}
```

**Step 4: Create minimal JS for tooltips**

```javascript
// tools/edps/web/static/app.js

// Auto-save debouncing
let saveTimeout = null;
const SAVE_DELAY = 5000; // 5 seconds

function queueSave(form) {
    if (saveTimeout) {
        clearTimeout(saveTimeout);
    }
    saveTimeout = setTimeout(() => {
        htmx.trigger(form, 'save');
    }, SAVE_DELAY);
}

// Attach to all auto-save forms
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-autosave]').forEach(form => {
        form.addEventListener('input', () => queueSave(form));
    });
});

// Show save indicator briefly
document.body.addEventListener('htmx:afterSwap', (event) => {
    if (event.detail.target.classList.contains('save-indicator')) {
        event.detail.target.style.opacity = '1';
        setTimeout(() => {
            event.detail.target.style.opacity = '0';
        }, 2000);
    }
});
```

**Step 5: Commit**

```bash
git add tools/edps/web/templates/ tools/edps/web/static/
git commit -m "feat(web): add base template with scholarly styling"
```

---

## Task 4: Configure Jinja2 Templates in FastAPI

**Files:**
- Modify: `tools/edps/web/app.py`

**Step 1: Add template configuration**

```python
# tools/edps/web/app.py
"""FastAPI application for EDPS web UI."""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "EDPS Reading Dashboard",
    })
```

**Step 2: Commit**

```bash
git add tools/edps/web/app.py
git commit -m "feat(web): configure Jinja2 templates"
```

---

## Task 5: Book List Page (Index)

**Files:**
- Create: `tools/edps/web/templates/index.html`
- Create: `tools/edps/web/routes.py`
- Modify: `tools/edps/web/app.py`

**Step 1: Create routes module**

```python
# tools/edps/web/routes.py
"""Route handlers for EDPS web UI."""
from pathlib import Path
from typing import Optional

import yaml

from edps.core.state import detect_book_state


def load_registry(books_dir: Path) -> list[dict]:
    """Load book registry with state info."""
    registry_path = books_dir / "_registry.yaml"
    if not registry_path.exists():
        return []

    data = yaml.safe_load(registry_path.read_text())
    books = data.get("books", [])

    # Enrich with state info
    for book in books:
        book_dir = books_dir / book["slug"]
        if book_dir.exists():
            state = detect_book_state(book_dir)
            book["state"] = {
                "total_sections": state.total_sections,
                "completed": state.total_sections - len(state.pending_sections),
                "has_content": state.ingested,
            }
        else:
            book["state"] = {
                "total_sections": 0,
                "completed": 0,
                "has_content": False,
            }

    return books


def load_book(books_dir: Path, slug: str) -> Optional[dict]:
    """Load a single book with full details."""
    registry = load_registry(books_dir)
    book = next((b for b in registry if b["slug"] == slug), None)
    if not book:
        return None

    book_dir = books_dir / slug

    # Load sections from sections.yaml
    sections_path = book_dir / "sections.yaml"
    if sections_path.exists():
        sections_data = yaml.safe_load(sections_path.read_text())
        sections = sections_data.get("sections", [])

        # Enrich sections with file existence info
        for section in sections:
            section_dir = book_dir / "sections" / section["id"]
            section["files"] = {
                "summary": (section_dir / "summary.md").exists(),
                "recall": (section_dir / "recall.md").exists(),
                "quiz": (section_dir / "quiz.md").exists(),
                "podcast": (section_dir / "podcast.md").exists(),
            }
            # Check if quiz has been evaluated (has feedback)
            quiz_path = section_dir / "quiz.md"
            if quiz_path.exists():
                content = quiz_path.read_text()
                section["has_feedback"] = "## Summary" in content or "## AI Feedback" in content
            else:
                section["has_feedback"] = False

        book["sections"] = sections
    else:
        book["sections"] = []

    return book


def load_section(books_dir: Path, slug: str, section_id: str) -> Optional[dict]:
    """Load a section with all its content."""
    book = load_book(books_dir, slug)
    if not book:
        return None

    section = next((s for s in book.get("sections", []) if s["id"] == section_id), None)
    if not section:
        return None

    section_dir = books_dir / slug / "sections" / section_id

    # Load file contents
    for file_type in ["summary", "recall", "quiz", "podcast"]:
        file_path = section_dir / f"{file_type}.md"
        if file_path.exists():
            section[f"{file_type}_content"] = file_path.read_text()
        else:
            section[f"{file_type}_content"] = None

    section["book"] = book
    return section
```

**Step 2: Create index template**

```html
<!-- tools/edps/web/templates/index.html -->
{% extends "base.html" %}

{% block title %}EDPS Reading Dashboard{% endblock %}

{% block content %}
<header class="mb-12">
    <h1 class="text-4xl font-semibold text-text mb-2">EDPS Reading Dashboard</h1>
    <p class="text-muted text-lg">Foundational texts for lasting knowledge</p>
</header>

{% set in_progress = books | selectattr('status', 'eq', 'in_progress') | list %}
{% set planned = books | selectattr('status', 'eq', 'planned') | list %}

{% if in_progress %}
<section class="mb-12">
    <h2 class="text-xl font-semibold text-muted uppercase tracking-wide mb-6">In Progress</h2>

    <div class="space-y-4">
    {% for book in in_progress %}
        <a href="/book/{{ book.slug }}" class="block card bg-surface p-6 rounded-lg hover:shadow-lg transition-shadow">
            <div class="flex justify-between items-start">
                <div>
                    <h3 class="text-xl font-semibold">{{ book.title }}</h3>
                    <p class="text-muted">{{ book.author }}, {{ book.year }}</p>
                </div>
                <div class="text-right">
                    <span class="font-mono text-sm">{{ book.state.completed }}/{{ book.state.total_sections }}</span>
                    <div class="w-32 h-2 bg-cream rounded-full mt-1 overflow-hidden">
                        {% set pct = (book.state.completed / book.state.total_sections * 100) if book.state.total_sections > 0 else 0 %}
                        <div class="progress-bar h-full rounded-full" style="width: {{ pct }}%"></div>
                    </div>
                </div>
            </div>
        </a>
    {% endfor %}
    </div>
</section>
{% endif %}

{% if planned %}
<section>
    <h2 class="text-xl font-semibold text-muted uppercase tracking-wide mb-6">Planned</h2>

    <div class="space-y-3">
    {% for book in planned %}
        <div class="card bg-surface/50 p-4 rounded-lg opacity-75">
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="text-lg">{{ book.title }}</h3>
                    <p class="text-muted text-sm">{{ book.author }}, {{ book.year }}</p>
                </div>
                <span class="text-muted text-sm">{{ book.category }}</span>
            </div>
        </div>
    {% endfor %}
    </div>
</section>
{% endif %}

{% endblock %}
```

**Step 3: Update app.py to use routes**

```python
# tools/edps/web/app.py
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
```

**Step 4: Test manually**

```bash
cd /Users/varunr/projects/edps-method
PYTHONPATH="$PWD/tools" python -m edps.cli run --no-browser &
sleep 2
curl http://localhost:8000/ | head -50
kill %1
```

Expected: HTML response with book list

**Step 5: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): add book list index page"
```

---

## Task 6: Book Detail Page

**Files:**
- Create: `tools/edps/web/templates/book.html`
- Modify: `tools/edps/web/app.py`

**Step 1: Create book template**

```html
<!-- tools/edps/web/templates/book.html -->
{% extends "base.html" %}

{% block title %}{{ book.title }} - EDPS{% endblock %}

{% block content %}
<nav class="mb-8">
    <a href="/" class="text-muted hover:text-accent transition-colors">&larr; All Books</a>
</nav>

<header class="mb-12">
    <h1 class="text-3xl font-semibold mb-2">{{ book.title }}</h1>
    <p class="text-muted text-lg">{{ book.author }} &middot; {{ book.year }}</p>

    <div class="mt-6 flex items-center gap-4">
        <div class="flex-1">
            <div class="w-full h-3 bg-cream rounded-full overflow-hidden">
                {% set pct = (book.state.completed / book.state.total_sections * 100) if book.state.total_sections > 0 else 0 %}
                <div class="progress-bar h-full rounded-full" style="width: {{ pct }}%"></div>
            </div>
        </div>
        <span class="font-mono text-sm text-muted">{{ book.state.completed }}/{{ book.state.total_sections }} sections</span>
    </div>
</header>

<section>
    <h2 class="text-xl font-semibold text-muted uppercase tracking-wide mb-6">Sections</h2>

    <div class="space-y-3">
    {% for section in book.sections %}
        {% set is_complete = section.files.recall and section.has_feedback %}
        {% set is_started = section.files.summary %}

        <a href="/book/{{ book.slug }}/{{ section.id }}"
           class="block card bg-surface p-4 rounded-lg hover:shadow-lg transition-shadow {% if not is_started %}opacity-50{% endif %}">
            <div class="flex items-center gap-4">
                <!-- Status icon -->
                <div class="w-8 h-8 flex items-center justify-center rounded-full
                    {% if is_complete %}bg-success/20 text-success
                    {% elif is_started %}bg-accent/20 text-accent
                    {% else %}bg-muted/20 text-muted{% endif %}">
                    {% if is_complete %}&#10003;
                    {% elif is_started %}&#9679;
                    {% else %}&#9675;{% endif %}
                </div>

                <!-- Section info -->
                <div class="flex-1">
                    <div class="flex items-baseline gap-2">
                        <span class="font-mono text-sm text-muted">{{ section.id }}</span>
                        <h3 class="font-medium">{{ section.title }}</h3>
                    </div>
                    {% if section.word_count %}
                    <p class="text-muted text-sm">~{{ (section.word_count / 250) | round | int }} min read</p>
                    {% endif %}
                </div>

                <!-- File indicators -->
                <div class="flex gap-2 text-xs">
                    <span class="{% if section.files.summary %}text-success{% else %}text-muted/50{% endif %}" title="Summary">S</span>
                    <span class="{% if section.files.recall %}text-success{% else %}text-muted/50{% endif %}" title="Recall">R</span>
                    <span class="{% if section.files.quiz %}text-success{% else %}text-muted/50{% endif %}" title="Quiz">Q</span>
                    <span class="{% if section.files.podcast %}text-success{% else %}text-muted/50{% endif %}" title="Podcast">P</span>
                </div>
            </div>
        </a>
    {% endfor %}
    </div>
</section>
{% endblock %}
```

**Step 2: Add route to app.py**

Add this route to `tools/edps/web/app.py`:

```python
@app.get("/book/{slug}")
async def book_detail(request: Request, slug: str):
    """Book detail page with section list."""
    books_dir = get_books_dir()
    book = load_book(books_dir, slug)

    if not book:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Book not found")

    return templates.TemplateResponse("book.html", {
        "request": request,
        "book": book,
    })
```

**Step 3: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): add book detail page with section list"
```

---

## Task 7: Section Workspace - Basic Structure

**Files:**
- Create: `tools/edps/web/templates/section.html`
- Modify: `tools/edps/web/app.py`

**Step 1: Create section template with tabs**

```html
<!-- tools/edps/web/templates/section.html -->
{% extends "base.html" %}

{% block title %}{{ section.title }} - {{ section.book.title }}{% endblock %}

{% block content %}
<nav class="mb-8 flex justify-between items-center">
    <a href="/book/{{ section.book.slug }}" class="text-muted hover:text-accent transition-colors">
        &larr; {{ section.book.title }}
    </a>
    <span class="text-muted text-sm">Section {{ section.id }} of {{ section.book.sections | length }}</span>
</nav>

<header class="mb-8">
    <h1 class="text-2xl font-semibold">{{ section.title }}</h1>
</header>

<!-- Tabs -->
<div class="border-b border-muted/20 mb-8">
    <nav class="flex gap-8">
        <a href="?tab=summary"
           class="tab py-3 px-1 text-lg {% if tab == 'summary' %}active text-text{% else %}text-muted hover:text-text{% endif %} {% if not section.summary_content %}opacity-50{% endif %}">
            Summary
        </a>
        <a href="?tab=recall"
           class="tab py-3 px-1 text-lg {% if tab == 'recall' %}active text-text{% else %}text-muted hover:text-text{% endif %} {% if not section.files.summary %}opacity-50 pointer-events-none{% endif %}">
            Recall
        </a>
        <a href="?tab=quiz"
           class="tab py-3 px-1 text-lg {% if tab == 'quiz' %}active text-text{% else %}text-muted hover:text-text{% endif %} {% if not section.files.quiz %}opacity-50 pointer-events-none{% endif %}">
            Quiz
        </a>
        <a href="?tab=podcast"
           class="tab py-3 px-1 text-lg {% if tab == 'podcast' %}active text-text{% else %}text-muted hover:text-text{% endif %} {% if not section.files.podcast %}opacity-50 pointer-events-none{% endif %}">
            Podcast
        </a>
    </nav>
</div>

<!-- Tab content -->
<div class="tab-content">
    {% if tab == 'summary' %}
        {% include "partials/tab_summary.html" %}
    {% elif tab == 'recall' %}
        {% include "partials/tab_recall.html" %}
    {% elif tab == 'quiz' %}
        {% include "partials/tab_quiz.html" %}
    {% elif tab == 'podcast' %}
        {% include "partials/tab_podcast.html" %}
    {% endif %}
</div>
{% endblock %}
```

**Step 2: Add route to app.py**

```python
@app.get("/book/{slug}/{section_id}")
async def section_workspace(request: Request, slug: str, section_id: str, tab: str = "summary"):
    """Section workspace with tabs."""
    books_dir = get_books_dir()
    section = load_section(books_dir, slug, section_id)

    if not section:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Section not found")

    # Default to summary tab, or first available
    if tab not in ["summary", "recall", "quiz", "podcast"]:
        tab = "summary"

    return templates.TemplateResponse("section.html", {
        "request": request,
        "section": section,
        "tab": tab,
    })
```

**Step 3: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): add section workspace with tab navigation"
```

---

## Task 8: Summary Tab (Read-Only)

**Files:**
- Create: `tools/edps/web/templates/partials/tab_summary.html`
- Create: `tools/edps/web/parsers.py`

**Step 1: Create markdown parser for summary**

```python
# tools/edps/web/parsers.py
"""Parsers for converting markdown content to structured data."""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SummaryData:
    """Parsed summary.md content."""
    tldr: str = ""
    key_terms: list[tuple[str, str]] = field(default_factory=list)  # (term, definition)
    argument_steps: list[str] = field(default_factory=list)
    modern_application: str = ""
    source_pointers: dict = field(default_factory=dict)


def parse_summary(content: str) -> SummaryData:
    """Parse summary.md into structured data."""
    data = SummaryData()

    # TLDR
    tldr_match = re.search(r'## TLDR\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if tldr_match:
        data.tldr = tldr_match.group(1).strip()

    # Key Terms
    terms_match = re.search(r'## Key Terms\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if terms_match:
        terms_text = terms_match.group(1)
        # Match "- **term**: definition" pattern
        for match in re.finditer(r'-\s*\*\*(.+?)\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', terms_text, re.DOTALL):
            data.key_terms.append((match.group(1).strip(), match.group(2).strip()))

    # Argument Structure
    arg_match = re.search(r'## Argument Structure\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if arg_match:
        arg_text = arg_match.group(1)
        # Match numbered steps
        for match in re.finditer(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\Z)', arg_text, re.DOTALL):
            data.argument_steps.append(match.group(1).strip())

    # Modern Application
    modern_match = re.search(r'## Modern Application\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if modern_match:
        data.modern_application = modern_match.group(1).strip()

    # Source Pointers
    source_match = re.search(r'## Source Pointers\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if source_match:
        source_text = source_match.group(1)
        for match in re.finditer(r'-\s*\*\*(.+?)\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', source_text, re.DOTALL):
            data.source_pointers[match.group(1).strip()] = match.group(2).strip()

    return data
```

**Step 2: Create summary tab template**

```html
<!-- tools/edps/web/templates/partials/tab_summary.html -->
{% if section.summary_content %}
    {% set summary = parse_summary(section.summary_content) %}

    <!-- TLDR -->
    <div class="card bg-surface p-6 rounded-lg mb-6">
        <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-3">TLDR</h3>
        <blockquote class="text-xl leading-relaxed border-l-4 border-accent pl-4 italic">
            {{ summary.tldr }}
        </blockquote>
    </div>

    <!-- Key Terms -->
    {% if summary.key_terms %}
    <div class="card bg-surface p-6 rounded-lg mb-6">
        <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-4">Key Terms</h3>
        <dl class="space-y-3">
            {% for term, definition in summary.key_terms %}
            <div>
                <dt class="font-semibold text-accent">{{ term }}</dt>
                <dd class="text-text/90 ml-4">{{ definition }}</dd>
            </div>
            {% endfor %}
        </dl>
    </div>
    {% endif %}

    <!-- Argument Structure -->
    {% if summary.argument_steps %}
    <div class="card bg-surface p-6 rounded-lg mb-6">
        <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-4">Argument Structure</h3>
        <ol class="space-y-3">
            {% for step in summary.argument_steps %}
            <li class="flex items-start gap-3">
                <span class="flex-shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-sm flex items-center justify-center font-mono">{{ loop.index }}</span>
                <span>{{ step }}</span>
            </li>
            {% endfor %}
        </ol>
    </div>
    {% endif %}

    <!-- Modern Application (collapsible) -->
    {% if summary.modern_application %}
    <details class="card bg-surface p-6 rounded-lg mb-6">
        <summary class="text-lg font-semibold text-muted uppercase tracking-wide cursor-pointer">Modern Application</summary>
        <div class="mt-4 text-text/90 leading-relaxed">
            {{ summary.modern_application }}
        </div>
    </details>
    {% endif %}

    <!-- Source Pointers (collapsible) -->
    {% if summary.source_pointers %}
    <details class="card bg-surface p-6 rounded-lg">
        <summary class="text-lg font-semibold text-muted uppercase tracking-wide cursor-pointer">Source Pointers</summary>
        <dl class="mt-4 space-y-3">
            {% for key, value in summary.source_pointers.items() %}
            <div>
                <dt class="font-medium text-muted">{{ key }}</dt>
                <dd class="text-text/90 ml-4">{{ value }}</dd>
            </div>
            {% endfor %}
        </dl>
    </details>
    {% endif %}

{% else %}
    <div class="text-center py-12 text-muted">
        <p class="text-lg">Summary not yet generated.</p>
        <p class="text-sm mt-2">Run <code class="bg-cream px-2 py-1 rounded">edps generate {{ section.book.slug }} {{ section.id }}</code></p>
    </div>
{% endif %}
```

**Step 3: Add parser to template context**

Update `tools/edps/web/app.py` to pass the parser:

```python
from edps.web.parsers import parse_summary

# In the section_workspace route, update the template response:
return templates.TemplateResponse("section.html", {
    "request": request,
    "section": section,
    "tab": tab,
    "parse_summary": parse_summary,
})
```

**Step 4: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): add summary tab with parsed content display"
```

---

## Task 9: Recall Tab (Form + Auto-Save)

**Files:**
- Create: `tools/edps/web/templates/partials/tab_recall.html`
- Add: `tools/edps/web/parsers.py` (extend)
- Modify: `tools/edps/web/app.py` (add save endpoint)

**Step 1: Add recall parser**

Add to `tools/edps/web/parsers.py`:

```python
@dataclass
class RecallData:
    """Parsed recall.md content for form population."""
    memory_points: list[str] = field(default_factory=list)
    after_reading: str = ""
    score: Optional[int] = None
    confidence: Optional[str] = None
    one_sentence: str = ""
    has_feedback: bool = False


def parse_recall(content: str) -> RecallData:
    """Parse recall.md into form-compatible data."""
    data = RecallData()

    # Check for feedback
    data.has_feedback = "## AI Feedback" in content

    # Memory points (5 numbered items)
    memory_match = re.search(r'## From Memory.*?\n\n.*?\n\n((?:\d+\..*?\n)+)', content, re.DOTALL)
    if memory_match:
        points_text = memory_match.group(1)
        points = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\Z)', points_text, re.DOTALL)
        data.memory_points = [p.strip() for p in points]

    # Pad to 5 points
    while len(data.memory_points) < 5:
        data.memory_points.append("")

    # After reading
    after_match = re.search(r'## After Selective Reading\s*\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if after_match:
        data.after_reading = after_match.group(1).strip()

    # Self-assessment score
    score_match = re.search(r'\*\*Score:\*\*\s*(\d)', content)
    if score_match:
        data.score = int(score_match.group(1))

    # Confidence
    conf_match = re.search(r'\*\*Confidence:\*\*\s*(\w+)', content)
    if conf_match:
        data.confidence = conf_match.group(1)

    # One sentence
    sentence_match = re.search(r'## One Sentence.*?\n\n(.+?)(?=\n---|\n##|\Z)', content, re.DOTALL)
    if sentence_match:
        data.one_sentence = sentence_match.group(1).strip()

    return data
```

**Step 2: Create recall tab template**

```html
<!-- tools/edps/web/templates/partials/tab_recall.html -->
{% set recall = parse_recall(section.recall_content) if section.recall_content else None %}

<form id="recall-form"
      data-autosave
      hx-post="/book/{{ section.book.slug }}/{{ section.id }}/save/recall"
      hx-trigger="save"
      hx-swap="innerHTML"
      hx-target="#save-indicator">

    <!-- From Memory -->
    <div class="card bg-surface p-6 rounded-lg mb-6">
        <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-2">From Memory</h3>
        <p class="text-muted text-sm mb-4">Write 5 key points before re-reading the source.</p>

        <div class="space-y-4">
            {% for i in range(5) %}
            <div class="flex gap-3">
                <span class="flex-shrink-0 w-6 h-6 rounded-full bg-muted/20 text-muted text-sm flex items-center justify-center font-mono">{{ i + 1 }}</span>
                <textarea
                    name="memory_{{ i }}"
                    rows="2"
                    class="flex-1 bg-cream/50 border border-muted/20 rounded-lg px-4 py-2 resize-none"
                    placeholder="Key point {{ i + 1 }}..."
                >{{ recall.memory_points[i] if recall else '' }}</textarea>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- After Reading -->
    <div class="card bg-surface p-6 rounded-lg mb-6">
        <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-2">After Selective Reading</h3>
        <p class="text-muted text-sm mb-4">What did you miss? What needs correction?</p>

        <textarea
            name="after_reading"
            rows="4"
            class="w-full bg-cream/50 border border-muted/20 rounded-lg px-4 py-3 resize-none"
            placeholder="Corrections and additions..."
        >{{ recall.after_reading if recall else '' }}</textarea>
    </div>

    <!-- Self-Assessment -->
    <div class="card bg-surface p-6 rounded-lg mb-6">
        <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-4">Self-Assessment</h3>

        <div class="flex flex-wrap gap-8">
            <div>
                <label class="block text-sm text-muted mb-2">Score (0-5)</label>
                <div class="flex gap-2">
                    {% for i in range(6) %}
                    <label class="cursor-pointer">
                        <input type="radio" name="score" value="{{ i }}" class="sr-only peer"
                            {% if recall and recall.score == i %}checked{% endif %}>
                        <span class="block w-10 h-10 rounded-full border-2 border-muted/30
                                     peer-checked:border-accent peer-checked:bg-accent/20
                                     flex items-center justify-center font-mono text-sm
                                     hover:border-muted transition-colors">{{ i }}</span>
                    </label>
                    {% endfor %}
                </div>
            </div>

            <div>
                <label class="block text-sm text-muted mb-2">Confidence</label>
                <div class="flex gap-2">
                    {% for level in ['Low', 'Medium', 'High'] %}
                    <label class="cursor-pointer">
                        <input type="radio" name="confidence" value="{{ level }}" class="sr-only peer"
                            {% if recall and recall.confidence == level %}checked{% endif %}>
                        <span class="block px-4 py-2 rounded-full border-2 border-muted/30
                                     peer-checked:border-accent peer-checked:bg-accent/20
                                     text-sm hover:border-muted transition-colors">{{ level }}</span>
                    </label>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <!-- One Sentence Summary -->
    <div class="card bg-surface p-6 rounded-lg mb-6">
        <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-2">One Sentence Summary</h3>
        <input
            type="text"
            name="one_sentence"
            class="w-full bg-cream/50 border border-muted/20 rounded-lg px-4 py-3"
            placeholder="Capture the essence in one sentence..."
            value="{{ recall.one_sentence if recall else '' }}">
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between">
        <span id="save-indicator" class="save-indicator opacity-0">Saved &#10003;</span>
        <button type="button"
                hx-post="/book/{{ section.book.slug }}/{{ section.id }}/evaluate/recall"
                hx-target="#recall-feedback"
                hx-swap="innerHTML"
                hx-indicator="#eval-spinner"
                class="bg-accent text-white px-6 py-2 rounded-lg hover:bg-accent/90 transition-colors">
            Get Feedback
        </button>
    </div>

    <div id="eval-spinner" class="htmx-indicator text-center py-4 text-muted">
        Evaluating...
    </div>
</form>

<!-- Feedback area -->
<div id="recall-feedback" class="mt-8">
    {% if recall and recall.has_feedback %}
        <!-- Show existing feedback -->
        <div class="card bg-surface p-6 rounded-lg border-l-4 border-success">
            <h3 class="text-lg font-semibold mb-4">Feedback</h3>
            <p class="text-muted">Feedback has been provided. See recall.md for details.</p>
        </div>
    {% endif %}
</div>
```

**Step 3: Add save endpoint**

Add to `tools/edps/web/app.py`:

```python
from fastapi import Form

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
    from edps.web.routes import write_recall

    books_dir = get_books_dir()
    write_recall(
        books_dir, slug, section_id,
        memory_points=[memory_0, memory_1, memory_2, memory_3, memory_4],
        after_reading=after_reading,
        score=score,
        confidence=confidence,
        one_sentence=one_sentence,
    )

    from fastapi.responses import HTMLResponse
    return HTMLResponse("Saved &#10003;")
```

**Step 4: Add write_recall to routes.py**

```python
def write_recall(
    books_dir: Path,
    slug: str,
    section_id: str,
    memory_points: list[str],
    after_reading: str,
    score: Optional[int],
    confidence: Optional[str],
    one_sentence: str,
) -> None:
    """Write recall data to recall.md, preserving feedback if present."""
    section_dir = books_dir / slug / "sections" / section_id
    recall_path = section_dir / "recall.md"

    # Read existing content to preserve feedback
    existing_feedback = ""
    if recall_path.exists():
        content = recall_path.read_text()
        feedback_match = re.search(r'(---\s*\n\n## AI Feedback.*)', content, re.DOTALL)
        if feedback_match:
            existing_feedback = feedback_match.group(1)

    # Build new content
    lines = [
        f"# Recall: Section {section_id}",
        "",
        "## From Memory",
        "",
        "*Write 5 key points from memory before re-reading.*",
        "",
    ]

    for i, point in enumerate(memory_points):
        lines.append(f"{i+1}. {point}")

    lines.extend([
        "",
        "## After Selective Reading",
        "",
        after_reading,
        "",
        "## Self-Assessment",
        "",
        f"**Score:** {score if score is not None else '_'}/5",
        f"**Confidence:** {confidence or '_'}",
        "",
        "## One Sentence Summary",
        "",
        one_sentence,
    ])

    if existing_feedback:
        lines.append("")
        lines.append(existing_feedback)

    recall_path.write_text("\n".join(lines))
```

**Step 5: Import re in routes.py**

Add `import re` at the top of `tools/edps/web/routes.py`.

**Step 6: Update section_workspace to pass parse_recall**

```python
from edps.web.parsers import parse_summary, parse_recall

# In section_workspace:
return templates.TemplateResponse("section.html", {
    "request": request,
    "section": section,
    "tab": tab,
    "parse_summary": parse_summary,
    "parse_recall": parse_recall,
})
```

**Step 7: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): add recall tab with auto-save form"
```

---

## Task 10: Quiz Tab (Form + Auto-Save)

**Files:**
- Create: `tools/edps/web/templates/partials/tab_quiz.html`
- Add: `tools/edps/web/parsers.py` (extend with quiz parser)
- Modify: `tools/edps/web/app.py` (add save endpoint)

**Step 1: Add quiz parser**

Add to `tools/edps/web/parsers.py`:

```python
@dataclass
class QuizQuestion:
    """A single quiz question."""
    number: str
    title: str
    question_type: str  # "mcq" or "prose"
    question_text: str
    options: list[str] = field(default_factory=list)  # For MCQ
    answer: str = ""
    feedback: Optional[str] = None  # Inline feedback if present


@dataclass
class QuizData:
    """Parsed quiz.md content."""
    questions: list[QuizQuestion] = field(default_factory=list)
    total_score: Optional[float] = None
    has_feedback: bool = False
    thematic_insights: Optional[str] = None
    tutors_note: Optional[str] = None


def parse_quiz(content: str) -> QuizData:
    """Parse quiz.md into form-compatible data."""
    data = QuizData()

    # Check for feedback
    data.has_feedback = "## Summary" in content or "## AI Feedback" in content

    # Extract score if present
    score_match = re.search(r'\*\*Score:\*\*\s*(\d+(?:\.\d+)?)/8', content)
    if score_match:
        data.total_score = float(score_match.group(1))

    # Parse questions
    # Pattern: ### N. Title\n\n[question]\n\n**Answer:** [answer]
    question_pattern = r'### (\d+)\.\s*(.+?)\n\n(.+?)\n\n\*\*Answer:\*\*\s*(.*?)(?=\n\n---|\n\n###|\n\n## |\Z)'

    for match in re.finditer(question_pattern, content, re.DOTALL):
        num, title, question_text, answer = match.groups()

        # Determine type: MCQ if has lettered options
        is_mcq = bool(re.search(r'\n[A-D]\)', question_text))

        q = QuizQuestion(
            number=num,
            title=title.strip(),
            question_type="mcq" if is_mcq else "prose",
            question_text=question_text.strip(),
            answer=answer.strip(),
        )

        # Extract MCQ options
        if is_mcq:
            options = re.findall(r'([A-D]\)\s*.+?)(?=\n[A-D]\)|\n\n|\Z)', question_text)
            q.options = [opt.strip() for opt in options]
            # Clean question text (remove options)
            q.question_text = re.split(r'\n[A-D]\)', question_text)[0].strip()

        data.questions.append(q)

    # Extract thematic insights
    insights_match = re.search(r'<summary>Thematic Insights</summary>\s*(.+?)</details>', content, re.DOTALL)
    if insights_match:
        data.thematic_insights = insights_match.group(1).strip()

    # Extract tutor's note
    tutor_match = re.search(r"<summary>Tutor's Note</summary>\s*(.+?)</details>", content, re.DOTALL)
    if tutor_match:
        data.tutors_note = tutor_match.group(1).strip()

    return data
```

**Step 2: Create quiz tab template**

```html
<!-- tools/edps/web/templates/partials/tab_quiz.html -->
{% set quiz = parse_quiz(section.quiz_content) if section.quiz_content else None %}

{% if quiz %}
<form id="quiz-form"
      data-autosave
      hx-post="/book/{{ section.book.slug }}/{{ section.id }}/save/quiz"
      hx-trigger="save"
      hx-swap="innerHTML"
      hx-target="#quiz-save-indicator">

    <div class="space-y-8">
    {% for q in quiz.questions %}
        <div class="card bg-surface p-6 rounded-lg">
            <div class="flex items-baseline gap-3 mb-4">
                <span class="font-mono text-sm text-muted">Q{{ q.number }}</span>
                <h3 class="font-semibold">{{ q.title }}</h3>
            </div>

            <p class="text-text/90 mb-4">{{ q.question_text }}</p>

            {% if q.question_type == 'mcq' %}
                <!-- MCQ Options -->
                <div class="space-y-2 mb-4">
                {% for opt in q.options %}
                    <label class="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-cream/50">
                        <input type="radio"
                               name="q{{ q.number }}"
                               value="{{ opt[0] }}"
                               {% if q.answer and q.answer.startswith(opt[0]) %}checked{% endif %}
                               class="w-4 h-4 text-accent">
                        <span>{{ opt }}</span>
                    </label>
                {% endfor %}
                </div>
            {% else %}
                <!-- Prose answer -->
                <textarea
                    name="q{{ q.number }}"
                    rows="4"
                    class="w-full bg-cream/50 border border-muted/20 rounded-lg px-4 py-3 resize-none"
                    placeholder="Your answer..."
                >{{ q.answer }}</textarea>
            {% endif %}
        </div>
    {% endfor %}
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between mt-8">
        <span id="quiz-save-indicator" class="save-indicator opacity-0">Saved &#10003;</span>
        <button type="button"
                hx-post="/book/{{ section.book.slug }}/{{ section.id }}/evaluate/quiz"
                hx-target="#quiz-feedback"
                hx-swap="innerHTML"
                hx-indicator="#quiz-eval-spinner"
                class="bg-accent text-white px-6 py-2 rounded-lg hover:bg-accent/90 transition-colors">
            Get Feedback
        </button>
    </div>

    <div id="quiz-eval-spinner" class="htmx-indicator text-center py-4 text-muted">
        Evaluating...
    </div>
</form>

<!-- Feedback summary -->
<div id="quiz-feedback" class="mt-8">
    {% if quiz.has_feedback %}
    <div class="card bg-surface p-6 rounded-lg border-l-4 border-accent">
        <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">Feedback Summary</h3>
            {% if quiz.total_score is not none %}
            <span class="font-mono text-xl">{{ quiz.total_score | round(1) }}/8</span>
            {% endif %}
        </div>

        {% if quiz.thematic_insights %}
        <details class="mb-4">
            <summary class="text-muted cursor-pointer">Thematic Insights</summary>
            <div class="mt-2 text-sm">{{ quiz.thematic_insights | safe }}</div>
        </details>
        {% endif %}

        {% if quiz.tutors_note %}
        <details>
            <summary class="text-muted cursor-pointer">Tutor's Note</summary>
            <div class="mt-2 text-sm italic">{{ quiz.tutors_note }}</div>
        </details>
        {% endif %}
    </div>
    {% endif %}
</div>

{% else %}
<div class="text-center py-12 text-muted">
    <p class="text-lg">Quiz not yet generated.</p>
    <p class="text-sm mt-2">Run <code class="bg-cream px-2 py-1 rounded">edps generate {{ section.book.slug }} {{ section.id }} --type quiz</code></p>
</div>
{% endif %}
```

**Step 3: Add quiz save endpoint to app.py**

```python
@app.post("/book/{slug}/{section_id}/save/quiz")
async def save_quiz(slug: str, section_id: str, request: Request):
    """Save quiz answers to quiz.md."""
    from edps.web.routes import update_quiz_answers

    form_data = await request.form()
    answers = {k: v for k, v in form_data.items() if k.startswith('q')}

    books_dir = get_books_dir()
    update_quiz_answers(books_dir, slug, section_id, answers)

    from fastapi.responses import HTMLResponse
    return HTMLResponse("Saved &#10003;")
```

**Step 4: Add update_quiz_answers to routes.py**

```python
def update_quiz_answers(books_dir: Path, slug: str, section_id: str, answers: dict[str, str]) -> None:
    """Update quiz answers in quiz.md, preserving structure and feedback."""
    section_dir = books_dir / slug / "sections" / section_id
    quiz_path = section_dir / "quiz.md"

    if not quiz_path.exists():
        return

    content = quiz_path.read_text()

    for q_key, answer in answers.items():
        # q_key is like "q1", "q2", etc.
        q_num = q_key[1:]  # Remove 'q' prefix

        # Pattern to find and replace the answer for this question
        # Matches: **Answer:** [anything until next section]
        pattern = rf'(### {q_num}\..+?\n\n\*\*Answer:\*\*\s*)(.+?)(\n\n---|\n\n###|\n\n## |\Z)'

        def replace_answer(m):
            return m.group(1) + answer + m.group(3)

        content = re.sub(pattern, replace_answer, content, flags=re.DOTALL)

    quiz_path.write_text(content)
```

**Step 5: Update section_workspace to pass parse_quiz**

```python
from edps.web.parsers import parse_summary, parse_recall, parse_quiz

# In section_workspace:
return templates.TemplateResponse("section.html", {
    "request": request,
    "section": section,
    "tab": tab,
    "parse_summary": parse_summary,
    "parse_recall": parse_recall,
    "parse_quiz": parse_quiz,
})
```

**Step 6: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): add quiz tab with auto-save form"
```

---

## Task 11: Podcast Tab (Read-Only)

**Files:**
- Create: `tools/edps/web/templates/partials/tab_podcast.html`

**Step 1: Create podcast tab template**

```html
<!-- tools/edps/web/templates/partials/tab_podcast.html -->
{% if section.podcast_content %}
    <div class="space-y-6">
        <!-- Audio player if exists -->
        {% set audio_path = "/books/" ~ section.book.slug ~ "/outputs/EDPS-" ~ section.book.slug ~ "-" ~ section.id ~ ".mp3" %}
        <div class="card bg-surface p-6 rounded-lg">
            <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-4">Audio</h3>
            <audio controls class="w-full">
                <source src="{{ audio_path }}" type="audio/mpeg">
                <p class="text-muted text-sm">Audio file not found. Generate with NotebookLM.</p>
            </audio>
        </div>

        <!-- Script -->
        <div class="card bg-surface p-6 rounded-lg">
            <h3 class="text-lg font-semibold text-muted uppercase tracking-wide mb-4">Script</h3>
            <div class="prose prose-lg max-w-none">
                {{ section.podcast_content | safe }}
            </div>
        </div>
    </div>
{% else %}
    <div class="text-center py-12 text-muted">
        <p class="text-lg">Podcast script not yet generated.</p>
        <p class="text-sm mt-2">Run <code class="bg-cream px-2 py-1 rounded">edps generate {{ section.book.slug }} {{ section.id }} --type podcast</code></p>
    </div>
{% endif %}
```

**Step 2: Commit**

```bash
git add tools/edps/web/templates/partials/
git commit -m "feat(web): add podcast tab with audio player"
```

---

## Task 12: Evaluate Endpoints

**Files:**
- Modify: `tools/edps/web/app.py`

**Step 1: Add evaluate recall endpoint**

```python
@app.post("/book/{slug}/{section_id}/evaluate/recall")
async def evaluate_recall_endpoint(slug: str, section_id: str):
    """Trigger AI evaluation of recall answers."""
    from edps.evaluation import evaluate_section
    from edps.config import load_config
    from fastapi.responses import HTMLResponse

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
```

**Step 2: Add evaluate quiz endpoint**

```python
@app.post("/book/{slug}/{section_id}/evaluate/quiz")
async def evaluate_quiz_endpoint(slug: str, section_id: str):
    """Trigger AI evaluation of quiz answers."""
    from edps.evaluation import evaluate_section
    from edps.config import load_config
    from fastapi.responses import HTMLResponse

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
```

**Step 3: Commit**

```bash
git add tools/edps/web/app.py
git commit -m "feat(web): add evaluation endpoints for recall and quiz"
```

---

## Task 13: Inline Feedback Highlights

**Files:**
- Modify: `tools/edps/web/parsers.py`
- Modify: `tools/edps/web/templates/partials/tab_quiz.html`

**Step 1: Enhance quiz parser to extract inline feedback**

Add to `parse_quiz` in `parsers.py`:

```python
def render_answer_with_highlights(answer: str) -> str:
    """Convert inline <details> feedback to hover tooltips."""
    # Pattern: text<details><summary>label</summary>feedback</details>
    pattern = r'(<details>\s*<summary>(.+?)</summary>\s*(.+?)\s*</details>)'

    def replace_with_tooltip(m):
        full_match, label, feedback = m.groups()
        # Get the text before the details tag (the error text)
        return f'<span class="error-highlight">{label}<span class="tooltip">{feedback}</span></span>'

    # This is simplified - in practice we need to find the quoted text before each details block
    result = re.sub(pattern, replace_with_tooltip, answer, flags=re.DOTALL)
    return result
```

**Step 2: Update quiz template to use highlights**

In `tab_quiz.html`, update the prose answer display:

```html
{% if q.question_type != 'mcq' %}
    <!-- Prose answer with potential inline highlights -->
    {% if quiz.has_feedback %}
        <div class="prose prose-sm max-w-none p-4 bg-cream/30 rounded-lg">
            {{ render_highlights(q.answer) | safe }}
        </div>
    {% else %}
        <textarea
            name="q{{ q.number }}"
            rows="4"
            class="w-full bg-cream/50 border border-muted/20 rounded-lg px-4 py-3 resize-none"
            placeholder="Your answer..."
        >{{ q.answer }}</textarea>
    {% endif %}
{% endif %}
```

**Step 3: Pass render function to template**

Update `section_workspace` in `app.py`:

```python
from edps.web.parsers import parse_summary, parse_recall, parse_quiz, render_answer_with_highlights

return templates.TemplateResponse("section.html", {
    "request": request,
    "section": section,
    "tab": tab,
    "parse_summary": parse_summary,
    "parse_recall": parse_recall,
    "parse_quiz": parse_quiz,
    "render_highlights": render_answer_with_highlights,
})
```

**Step 4: Commit**

```bash
git add tools/edps/web/
git commit -m "feat(web): add inline feedback highlights with hover tooltips"
```

---

## Task 14: Polish and Testing

**Files:**
- Create: `tools/tests/test_web.py`

**Step 1: Create basic web tests**

```python
# tools/tests/test_web.py
"""Tests for EDPS web UI."""
import pytest
from fastapi.testclient import TestClient

from edps.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Health check returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_page_loads(client):
    """Index page renders without error."""
    response = client.get("/")
    assert response.status_code == 200
    assert "EDPS" in response.text
```

**Step 2: Run tests**

```bash
cd /Users/varunr/projects/edps-method/tools
source .venv/bin/activate
PYTHONPATH="$PWD" python -m pytest tests/test_web.py -v
```

Expected: Tests pass

**Step 3: Commit**

```bash
git add tools/tests/test_web.py
git commit -m "test(web): add basic web UI tests"
```

---

## Task 15: Final Integration Test

**Step 1: Manual end-to-end test**

```bash
cd /Users/varunr/projects/edps-method
PYTHONPATH="$PWD/tools" python -m edps.cli run
```

Test checklist:
- [ ] Index page shows books
- [ ] Clicking book shows sections
- [ ] Clicking section shows tabs
- [ ] Summary tab renders content
- [ ] Recall tab form saves (check file)
- [ ] Quiz tab form saves (check file)
- [ ] Get Feedback button works (if LLM configured)

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat(web): complete web UI implementation

- Book list with progress indicators
- Section workspace with tabs (Summary/Recall/Quiz/Podcast)
- Auto-save with 5s debounce
- AI evaluation integration
- Inline feedback highlights with tooltips
- Warm scholarly aesthetic"
```

---

## Summary

This plan implements the full web UI in 15 tasks:

| Task | Description | Files |
|------|-------------|-------|
| 1 | Web module structure | `web/__init__.py`, `web/app.py` |
| 2 | CLI run command | `commands/run.py` |
| 3 | Base template + styling | `templates/base.html`, `static/` |
| 4 | Jinja2 configuration | `web/app.py` |
| 5 | Book list page | `templates/index.html`, `routes.py` |
| 6 | Book detail page | `templates/book.html` |
| 7 | Section workspace | `templates/section.html` |
| 8 | Summary tab | `partials/tab_summary.html`, `parsers.py` |
| 9 | Recall tab + save | `partials/tab_recall.html` |
| 10 | Quiz tab + save | `partials/tab_quiz.html` |
| 11 | Podcast tab | `partials/tab_podcast.html` |
| 12 | Evaluate endpoints | `web/app.py` |
| 13 | Inline highlights | `parsers.py`, templates |
| 14 | Tests | `tests/test_web.py` |
| 15 | Integration test | Manual verification |

---

Plan complete and saved to `docs/plans/2025-12-29-web-ui-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
