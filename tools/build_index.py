#!/usr/bin/env python3
"""
build_index.py - Generate GitHub Pages site from EDPS Method data

Generates self-contained HTML with embedded CSS (no Jekyll dependency).
Warm, scholarly aesthetic with collapsible category accordions.
"""

import os
import yaml
from pathlib import Path
from datetime import datetime
from html import escape


# Paths
ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
SITE_DIR = ROOT / "site"

# Configuration
GITHUB_REPO = "https://github.com/varunr89/edps-method"
METHODOLOGY_URL = "./methodology.html"


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;0,700;1,400&family=Source+Sans+Pro:wght@400;600&display=swap');

:root {
  --cream: #f8f5ef;
  --cream-dark: #efe9dd;
  --brown: #3d3328;
  --brown-light: #5c4d3c;
  --gold: #8b7355;
  --gold-light: #a89070;
  --accent: #c4a574;
  --success: #5a7c5a;
  --active: #7a6a4a;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Source Sans Pro', Georgia, serif;
  background: var(--cream);
  color: var(--brown);
  line-height: 1.7;
  min-height: 100vh;
}

/* Subtle paper texture */
body::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%' height='100%' filter='url(%23noise)'/%3E%3C/svg%3E");
  opacity: 0.03;
  pointer-events: none;
  z-index: -1;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 3rem 2rem 4rem;
}

/* Hero Section */
.hero {
  text-align: center;
  padding: 2rem 0 3rem;
  border-bottom: 1px solid var(--cream-dark);
  margin-bottom: 2.5rem;
}

.hero h1 {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 2.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--brown);
  margin-bottom: 0.3rem;
}

.hero .subtitle {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.1rem;
  color: var(--gold);
  letter-spacing: 0.15em;
  margin-bottom: 0.5rem;
}

.hero .learn-more {
  font-size: 0.95rem;
  color: var(--gold-light);
  text-decoration: none;
  border-bottom: 1px dotted var(--gold-light);
  transition: all 0.2s ease;
}

.hero .learn-more:hover {
  color: var(--brown);
  border-color: var(--brown);
}

.intro {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.15rem;
  font-style: italic;
  color: var(--brown-light);
  max-width: 600px;
  margin: 1.5rem auto;
  line-height: 1.8;
}

/* Stats Cards */
.stats {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin: 2rem 0;
}

.stat-card {
  background: var(--cream-dark);
  padding: 1rem 1.5rem;
  border-radius: 4px;
  text-align: center;
  min-width: 90px;
}

.stat-card .number {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--brown);
}

.stat-card .label {
  font-size: 0.8rem;
  color: var(--gold);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* GitHub Link */
.github-link {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
  padding: 0.6rem 1.2rem;
  background: var(--brown);
  color: var(--cream);
  text-decoration: none;
  font-size: 0.9rem;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.github-link:hover {
  background: var(--brown-light);
}

.github-link svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

/* Currently Reading */
.currently-reading {
  background: linear-gradient(135deg, var(--cream-dark) 0%, #f0ebe0 100%);
  border: 1px solid #e5dfd0;
  border-radius: 6px;
  padding: 1.5rem;
  margin-bottom: 2.5rem;
}

.currently-reading h2 {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1rem;
  font-weight: 600;
  color: var(--gold);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.current-book {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.current-book .title {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--brown);
}

.current-book .author {
  color: var(--brown-light);
  font-size: 0.95rem;
}

.current-book .progress-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar-small {
  width: 120px;
  height: 6px;
  background: var(--cream);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-small .fill {
  height: 100%;
  background: var(--gold);
  transition: width 0.3s ease;
}

.current-book .continue-link {
  font-size: 0.9rem;
  color: var(--gold);
  text-decoration: none;
  font-weight: 600;
}

.current-book .continue-link:hover {
  color: var(--brown);
}

/* Section Header */
.section-header {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--gold);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-bottom: 1.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--cream-dark);
}

/* Accordion Categories */
.categories {
  margin-bottom: 3rem;
}

details.category {
  margin-bottom: 0.75rem;
  background: white;
  border: 1px solid #e8e3d8;
  border-radius: 4px;
  overflow: hidden;
}

details.category[open] {
  border-color: var(--gold-light);
}

summary.category-header {
  padding: 1rem 1.25rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  list-style: none;
  user-select: none;
  transition: background 0.15s ease;
}

summary.category-header::-webkit-details-marker {
  display: none;
}

summary.category-header:hover {
  background: var(--cream);
}

.category-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.category-title .arrow {
  font-size: 0.7rem;
  color: var(--gold);
  transition: transform 0.2s ease;
}

details.category[open] .arrow {
  transform: rotate(90deg);
}

.category-title h3 {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--brown);
}

.category-title .count {
  font-size: 0.85rem;
  color: var(--gold-light);
  font-weight: normal;
}

.category-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.category-progress {
  font-size: 0.85rem;
  color: var(--gold-light);
}

/* Book List inside accordion */
.book-list {
  padding: 0.5rem 1.25rem 1.25rem;
  border-top: 1px solid #eee;
}

.book-item {
  display: flex;
  align-items: center;
  padding: 0.6rem 0;
  border-bottom: 1px solid #f5f2ec;
}

.book-item:last-child {
  border-bottom: none;
}

.book-status {
  width: 20px;
  font-size: 0.9rem;
  color: var(--gold-light);
}

.book-status.in-progress {
  color: var(--active);
}

.book-status.completed {
  color: var(--success);
}

.book-info {
  flex: 1;
}

.book-info a {
  font-family: 'Crimson Pro', Georgia, serif;
  font-size: 1.05rem;
  color: var(--brown);
  text-decoration: none;
  transition: color 0.15s ease;
}

.book-info a:hover {
  color: var(--gold);
}

.book-info .author {
  font-size: 0.85rem;
  color: var(--brown-light);
  margin-left: 0.3rem;
}

/* Footer */
.footer {
  text-align: center;
  padding-top: 2rem;
  border-top: 1px solid var(--cream-dark);
  color: var(--gold-light);
  font-size: 0.85rem;
}

.footer a {
  color: var(--gold);
  text-decoration: none;
}

.footer a:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 600px) {
  .container {
    padding: 2rem 1.25rem;
  }

  .hero h1 {
    font-size: 2rem;
  }

  .stats {
    gap: 0.75rem;
  }

  .stat-card {
    padding: 0.75rem 1rem;
    min-width: 70px;
  }

  .stat-card .number {
    font-size: 1.5rem;
  }

  .current-book {
    flex-direction: column;
    align-items: flex-start;
  }
}
"""

GITHUB_ICON = '''<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'''


def read_yaml(path: Path) -> dict:
    """Read a YAML file, returning empty dict if not found."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def pct(done: int, total: int) -> int:
    """Calculate percentage, handling division by zero."""
    return 0 if total == 0 else round((done / total) * 100)


def status_symbol(status: str) -> tuple[str, str]:
    """Return (symbol, css_class) for status."""
    return {
        "planned": ("○", ""),
        "in_progress": ("◐", "in-progress"),
        "completed": ("●", "completed"),
    }.get(status, ("○", ""))


def generate_index_html(registry: dict, book_data: list) -> str:
    """Generate the main index.html page."""

    # Count stats
    total_books = len(book_data)
    in_progress_books = [b for b in book_data if b["meta"].get("status") == "in_progress"]
    in_progress_count = len(in_progress_books)
    completed_count = sum(1 for b in book_data if b["meta"].get("status") == "completed")

    # Group by category
    categories = {}
    for b in sorted(book_data, key=lambda x: x["meta"].get("priority", 999) if x["meta"].get("priority") else 999):
        cat = b["meta"].get("category", "Uncategorized")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(b)

    # Build currently reading section
    currently_reading_html = ""
    if in_progress_books:
        book = in_progress_books[0]
        slug = book["slug"]
        meta = book["meta"]
        title = meta.get("short_title", meta.get("title", slug))
        author = meta.get("author", "")
        sections = book["sections"].get("sections", [])
        total = len(sections)
        done = len(book["progress"].get("completed_sections", []))
        p = pct(done, total)

        currently_reading_html = f'''
    <div class="currently-reading">
      <h2>Currently Reading</h2>
      <div class="current-book">
        <div>
          <span class="title">{escape(title)}</span>
          <span class="author">— {escape(author)}</span>
        </div>
        <div class="progress-info">
          <div class="progress-bar-small">
            <div class="fill" style="width: {p}%"></div>
          </div>
          <span style="font-size: 0.85rem; color: var(--gold-light);">{p}% · {total} sections</span>
          <a href="./{slug}.html" class="continue-link">Continue →</a>
        </div>
      </div>
    </div>
'''

    # Build category accordions
    categories_html = ""
    for cat, books in categories.items():
        book_count = len(books)
        completed_in_cat = sum(1 for b in books if b["meta"].get("status") == "completed")
        cat_progress = pct(completed_in_cat, book_count)

        books_html = ""
        for b in books:
            slug = b["slug"]
            meta = b["meta"]
            title = meta.get("short_title", meta.get("title", slug))
            author = meta.get("author", "")
            status = meta.get("status", "planned")
            symbol, css_class = status_symbol(status)

            books_html += f'''
        <div class="book-item">
          <span class="book-status {css_class}">{symbol}</span>
          <div class="book-info">
            <a href="./{slug}.html">{escape(title)}</a>
            <span class="author">— {escape(author)}</span>
          </div>
        </div>'''

        categories_html += f'''
      <details class="category">
        <summary class="category-header">
          <div class="category-title">
            <span class="arrow">▶</span>
            <h3>{escape(cat)} <span class="count">({book_count})</span></h3>
          </div>
          <div class="category-meta">
            <span class="category-progress">{cat_progress}% complete</span>
          </div>
        </summary>
        <div class="book-list">{books_html}
        </div>
      </details>
'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The EDPS Method</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <h1>THE EDPS METHOD</h1>
      <p class="subtitle">Ebbinghaus · Dunlosky · Paivio · Sweller</p>
      <a href="{METHODOLOGY_URL}" class="learn-more">What is this? →</a>

      <p class="intro">
        I'm Varun, and I'm working through the foundational texts that shaped
        how we think about economics, politics, and human behavior. This page
        exists for public accountability—when others can see my progress,
        I show up consistently.
      </p>

      <div class="stats">
        <div class="stat-card">
          <div class="number">{total_books}</div>
          <div class="label">Books</div>
        </div>
        <div class="stat-card">
          <div class="number">{in_progress_count}</div>
          <div class="label">Active</div>
        </div>
        <div class="stat-card">
          <div class="number">{completed_count}</div>
          <div class="label">Done</div>
        </div>
      </div>

      <a href="{GITHUB_REPO}" class="github-link" target="_blank" rel="noopener">
        {GITHUB_ICON}
        View on GitHub
      </a>
    </header>

{currently_reading_html}
    <section class="categories">
      <h2 class="section-header">Reading Roadmap</h2>
{categories_html}
    </section>

    <footer class="footer">
      <p>Last updated: {datetime.now().strftime("%B %d, %Y")}</p>
      <p style="margin-top: 0.5rem;">Built with the EDPS Method · <a href="{GITHUB_REPO}">GitHub</a></p>
    </footer>
  </div>
</body>
</html>
'''


def generate_book_page_html(slug: str, meta: dict, sections: dict, progress: dict) -> str:
    """Generate HTML content for a single book page."""
    title = meta.get("title", slug)
    short_title = meta.get("short_title", title)
    author = meta.get("author", "Unknown")
    year = meta.get("year", "")
    status = meta.get("status", "planned")
    category = meta.get("category", "")
    why = meta.get("why", "")

    section_list = sections.get("sections", [])
    total = len(section_list)
    completed_list = progress.get("completed_sections", [])
    completed_count = len(completed_list)
    p = pct(completed_count, total)
    completed_set = set(completed_list)

    symbol, css_class = status_symbol(status)
    status_text = status.replace('_', ' ').title()

    # Build sections list
    sections_html = ""
    for sec in section_list:
        sec_id = sec.get("id", "")
        sec_title = sec.get("title", "")
        location = sec.get("location", "")
        is_done = sec_id in completed_set
        check = "●" if is_done else "○"
        check_class = "completed" if is_done else ""
        sections_html += f'''
        <div class="book-item">
          <span class="book-status {check_class}">{check}</span>
          <div class="book-info">
            <span style="font-weight: 600;">{escape(sec_title)}</span>
            <span class="author">— {escape(location)}</span>
          </div>
        </div>'''

    why_html = f'<blockquote style="font-style: italic; color: var(--brown-light); border-left: 3px solid var(--gold-light); padding-left: 1rem; margin: 1.5rem 0;">{escape(why)}</blockquote>' if why else ""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(short_title)} — EDPS Method</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="container">
    <p style="margin-bottom: 2rem;"><a href="./index.html" style="color: var(--gold); text-decoration: none;">← Back to Reading List</a></p>

    <header style="margin-bottom: 2rem;">
      <h1 style="font-family: 'Crimson Pro', Georgia, serif; font-size: 2rem; margin-bottom: 0.5rem;">{escape(short_title)}</h1>
      <p style="color: var(--brown-light); font-size: 1.1rem;">{escape(author)} ({year})</p>
      <p style="color: var(--gold); font-size: 0.9rem; margin-top: 0.5rem;">{escape(category)}</p>
    </header>

    {why_html}

    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem;">
      <span class="book-status {css_class}" style="font-size: 1.2rem;">{symbol}</span>
      <span style="color: var(--brown-light);">{status_text}</span>
      <span style="color: var(--gold-light);">·</span>
      <span style="color: var(--gold-light);">{completed_count}/{total} sections ({p}%)</span>
    </div>

    <div class="progress-bar-small" style="width: 100%; height: 8px; margin-bottom: 2rem;">
      <div class="fill" style="width: {p}%;"></div>
    </div>

    <section>
      <h2 class="section-header">Sections</h2>
      <div class="book-list" style="background: white; border: 1px solid #e8e3d8; border-radius: 4px; padding: 1rem;">
        {sections_html if sections_html else '<p style="color: var(--gold-light); font-style: italic;">No sections defined yet.</p>'}
      </div>
    </section>

    <footer class="footer" style="margin-top: 3rem;">
      <p><a href="{GITHUB_REPO}">View on GitHub</a></p>
    </footer>
  </div>
</body>
</html>
'''


def generate_methodology_page() -> str:
    """Generate the methodology page linking to the workflow document."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The EDPS Method — Methodology</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="container">
    <p style="margin-bottom: 2rem;"><a href="./index.html" style="color: var(--gold); text-decoration: none;">← Back to Reading List</a></p>

    <header class="hero" style="border-bottom: none; padding-bottom: 1rem;">
      <h1>THE EDPS METHOD</h1>
      <p class="subtitle">Ebbinghaus · Dunlosky · Paivio · Sweller</p>
    </header>

    <section style="max-width: 650px; margin: 0 auto;">
      <h2 style="font-family: 'Crimson Pro', Georgia, serif; font-size: 1.5rem; margin-bottom: 1rem; color: var(--brown);">The Science Behind Deep Reading</h2>

      <p style="margin-bottom: 1.5rem; line-height: 1.8;">
        The EDPS Method synthesizes four foundational discoveries in cognitive science to transform
        how we extract and retain knowledge from important texts.
      </p>

      <div style="background: white; border: 1px solid #e8e3d8; border-radius: 4px; padding: 1.5rem; margin-bottom: 1.5rem;">
        <h3 style="font-family: 'Crimson Pro', Georgia, serif; color: var(--gold); margin-bottom: 0.75rem;">Hermann Ebbinghaus (1885)</h3>
        <p style="color: var(--brown-light);">Discovered the forgetting curve and spaced repetition. We forget 70% within 24 hours—unless we review at expanding intervals.</p>
      </div>

      <div style="background: white; border: 1px solid #e8e3d8; border-radius: 4px; padding: 1.5rem; margin-bottom: 1.5rem;">
        <h3 style="font-family: 'Crimson Pro', Georgia, serif; color: var(--gold); margin-bottom: 0.75rem;">John Dunlosky (2013)</h3>
        <p style="color: var(--brown-light);">Meta-analysis of learning techniques. Active recall and practice testing vastly outperform passive re-reading and highlighting.</p>
      </div>

      <div style="background: white; border: 1px solid #e8e3d8; border-radius: 4px; padding: 1.5rem; margin-bottom: 1.5rem;">
        <h3 style="font-family: 'Crimson Pro', Georgia, serif; color: var(--gold); margin-bottom: 0.75rem;">Allan Paivio (1971)</h3>
        <p style="color: var(--brown-light);">Dual coding theory. Information encoded both verbally and visually creates stronger, more retrievable memories.</p>
      </div>

      <div style="background: white; border: 1px solid #e8e3d8; border-radius: 4px; padding: 1.5rem; margin-bottom: 1.5rem;">
        <h3 style="font-family: 'Crimson Pro', Georgia, serif; color: var(--gold); margin-bottom: 0.75rem;">John Sweller (1988)</h3>
        <p style="color: var(--brown-light);">Cognitive load theory. Working memory is limited. Chunking, scaffolding, and progressive complexity prevent overload.</p>
      </div>

      <h2 style="font-family: 'Crimson Pro', Georgia, serif; font-size: 1.5rem; margin: 2rem 0 1rem; color: var(--brown);">The Workflow</h2>

      <p style="margin-bottom: 1rem; line-height: 1.8;">
        For each book section, I follow a structured process:
      </p>

      <ol style="margin-left: 1.5rem; line-height: 2;">
        <li><strong>Read</strong> the section carefully</li>
        <li><strong>Summarize</strong> key arguments (AI-assisted)</li>
        <li><strong>Quiz</strong> myself on the content</li>
        <li><strong>Recall</strong> from memory before checking notes</li>
        <li><strong>Synthesize</strong> weekly across sections</li>
        <li><strong>Map</strong> ideas to modern applications</li>
      </ol>

      <p style="margin-top: 1.5rem; line-height: 1.8;">
        Public accountability ensures consistency. When my progress is visible, I show up.
      </p>
    </section>

    <footer class="footer" style="margin-top: 3rem;">
      <p><a href="{GITHUB_REPO}">View full methodology on GitHub</a></p>
    </footer>
  </div>
</body>
</html>
'''


def main():
    """Main build function."""

    # Ensure site directory exists
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # Read registry
    registry = read_yaml(BOOKS_DIR / "_registry.yaml")
    books_list = registry.get("books", [])

    # Collect all book data
    book_data = []
    for entry in books_list:
        if not isinstance(entry, dict):
            continue
        slug = entry.get("slug")
        if not slug or not isinstance(slug, str):
            continue

        book_dir = BOOKS_DIR / slug
        meta = read_yaml(book_dir / "meta.yaml")
        sections = read_yaml(book_dir / "sections.yaml")
        progress = read_yaml(book_dir / "progress.yaml")

        # Merge registry entry with meta (registry takes precedence)
        for key in ["status", "priority", "category", "title", "author", "year", "why", "tags", "short_title"]:
            if key in entry:
                meta[key] = entry[key]

        book_data.append({
            "slug": slug,
            "meta": meta,
            "sections": sections,
            "progress": progress,
        })

    # Generate book pages
    for b in book_data:
        slug = b["slug"]
        page_content = generate_book_page_html(slug, b["meta"], b["sections"], b["progress"])
        (SITE_DIR / f"{slug}.html").write_text(page_content, encoding="utf-8")
        print(f"Generated: site/{slug}.html")

    # Generate index
    index_content = generate_index_html(registry, book_data)
    (SITE_DIR / "index.html").write_text(index_content, encoding="utf-8")
    print("Generated: site/index.html")

    # Generate methodology page
    methodology_content = generate_methodology_page()
    (SITE_DIR / "methodology.html").write_text(methodology_content, encoding="utf-8")
    print("Generated: site/methodology.html")

    print("\nBuild complete!")


if __name__ == "__main__":
    main()
