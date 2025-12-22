#!/usr/bin/env python3
"""
build_index.py - Generate GitHub Pages site from EDPS Method data

Reads:
  - books/_registry.yaml (roadmap across books)
  - books/<slug>/meta.yaml (book metadata)
  - books/<slug>/sections.yaml (section plan)
  - books/<slug>/progress.yaml (completion tracking)

Writes:
  - site/index.md (main roadmap page)
  - site/books.md (list of all books)
  - site/<slug>.md (per-book detail pages)
"""

import os
import yaml
from pathlib import Path
from datetime import datetime


# Paths
ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
SITE_DIR = ROOT / "site"


def read_yaml(path: Path) -> dict:
    """Read a YAML file, returning empty dict if not found."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def pct(done: int, total: int) -> int:
    """Calculate percentage, handling division by zero."""
    return 0 if total == 0 else round((done / total) * 100)


def status_emoji(status: str) -> str:
    """Return emoji for status."""
    return {
        "planned": "⚪",
        "in_progress": "🟡",
        "completed": "🟢",
    }.get(status, "⚪")


def generate_book_page(slug: str, meta: dict, sections: dict, progress: dict) -> str:
    """Generate markdown content for a single book page."""
    title = meta.get("title", slug)
    short_title = meta.get("short_title", title)
    author = meta.get("author", "Unknown")
    year = meta.get("year", "")
    status = meta.get("status", "planned")
    category = meta.get("category", "")
    why = meta.get("why", "")

    section_list = sections.get("sections", [])
    total = len(section_list)
    completed = progress.get("completed_sections", [])
    completed_count = len(completed)
    p = pct(completed_count, total)

    # Build claims section
    claims = sections.get("claims", [])
    claims_md = ""
    if claims:
        claims_md = "## Core Claims\n\n"
        for i, claim in enumerate(claims, 1):
            claims_md += f"{i}. **{claim.get('id', '')}**: {claim.get('claim', '')}\n"
        claims_md += "\n"

    # Build sections table
    sections_md = "## Sections\n\n"
    sections_md += "| # | Title | Location | Priority | Status |\n"
    sections_md += "|---|-------|----------|----------|--------|\n"

    completed_set = set(completed)
    for sec in section_list:
        sec_id = sec.get("id", "")
        sec_title = sec.get("title", "")
        location = sec.get("location", "")
        priority = sec.get("priority", "")
        is_done = "✅" if sec_id in completed_set else "⬜"
        sections_md += f"| {sec_id} | {sec_title} | {location} | {priority} | {is_done} |\n"

    # Build stats section
    stats = progress.get("stats", {})
    stats_md = ""
    if stats:
        stats_md = "## Stats\n\n"
        stats_md += f"- **Current streak**: {stats.get('current_streak', 0)} days\n"
        stats_md += f"- **Longest streak**: {stats.get('longest_streak', 0)} days\n"
        avg_quiz = stats.get('average_quiz_score')
        if avg_quiz:
            stats_md += f"- **Average quiz score**: {avg_quiz}/8\n"
        avg_recall = stats.get('average_recall_score')
        if avg_recall:
            stats_md += f"- **Average recall score**: {avg_recall}/5\n"
        stats_md += "\n"

    # Category line
    category_md = f"**Category**: {category}\n" if category else ""

    # Why line
    why_md = f"\n> {why}\n" if why else ""

    return f"""---
layout: default
title: "{short_title}"
---

# {short_title}

**Author**: {author} ({year})
{category_md}**Status**: {status_emoji(status)} {status.replace('_', ' ').title()}
**Progress**: {completed_count}/{total} sections ({p}%)

{"█" * (p // 5)}{"░" * (20 - p // 5)} {p}%
{why_md}
---

{claims_md}
{sections_md}

---

{stats_md}
## Final Outputs

- [One-Pager](../books/{slug}/outputs/one-pager.md)
- [Teachable Outline](../books/{slug}/outputs/teachable-outline.md)
- [Question Bank](../books/{slug}/outputs/question-bank.md)
- [Modern Mapping](../books/{slug}/outputs/modern-mapping.md)
"""


def generate_index(registry: dict, book_data: list) -> str:
    """Generate the main index.md page."""

    # Count stats
    total_books = len(book_data)
    in_progress = sum(1 for b in book_data if b["meta"].get("status") == "in_progress")
    completed = sum(1 for b in book_data if b["meta"].get("status") == "completed")

    # Group by category
    categories = {}
    for b in sorted(book_data, key=lambda x: x["meta"].get("priority", 999) if x["meta"].get("priority") else 999):
        cat = b["meta"].get("category", "Uncategorized")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(b)

    # Build categorized sections
    roadmap_md = ""
    for cat, books in categories.items():
        roadmap_md += f"\n### {cat}\n\n"
        roadmap_md += "| Book | Author | Status | Progress |\n"
        roadmap_md += "|------|--------|--------|----------|\n"

        for b in books:
            slug = b["slug"]
            meta = b["meta"]
            sections = b["sections"]
            progress = b["progress"]

            title = meta.get("short_title", meta.get("title", slug))
            author = meta.get("author", "")
            status = meta.get("status", "planned")

            section_list = sections.get("sections", [])
            total = len(section_list)
            done = len(progress.get("completed_sections", []))
            p = pct(done, total)

            progress_bar = f"{'█' * (p // 10)}{'░' * (10 - p // 10)}"

            roadmap_md += f"| [{title}](./{slug}.html) | {author} | {status_emoji(status)} | {progress_bar} {p}% |\n"

        roadmap_md += "\n"

    return f"""---
layout: default
title: "EDPS Method"
---

# The EDPS Method

> **E**bbinghaus · **D**unlosky · **P**aivio · **S**weller

A research-backed system for extracting lasting knowledge from important works.

---

## Stats

- **Total books**: {total_books}
- **In progress**: {in_progress}
- **Completed**: {completed}

---

## Reading Roadmap
{roadmap_md}

---

## Quick Links

- [All Books](./books.html)
- [Methodology](../workflow-diagram.md)
- [GitHub Repository](https://github.com/username/edps-method)

---

*Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""


def generate_books_page(book_data: list) -> str:
    """Generate the books.md listing page."""

    book_links = ""
    for b in sorted(book_data, key=lambda x: x["meta"].get("priority", 999) if x["meta"].get("priority") else 999):
        slug = b["slug"]
        meta = b["meta"]
        title = meta.get("title", slug)
        author = meta.get("author", "")
        year = meta.get("year", "")
        status = meta.get("status", "planned")

        book_links += f"- [{title}](./{slug}.html) — {author} ({year}) {status_emoji(status)}\n"

    return f"""---
layout: default
title: "Books"
---

# All Books

{book_links}
"""


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
        for key in ["status", "priority", "category", "title", "author", "year", "why", "tags"]:
            if key in entry:
                meta[key] = entry[key]

        book_data.append({
            "slug": slug,
            "meta": meta,
            "sections": sections,
            "progress": progress,
        })

    # Generate pages
    for b in book_data:
        slug = b["slug"]
        page_content = generate_book_page(slug, b["meta"], b["sections"], b["progress"])
        (SITE_DIR / f"{slug}.md").write_text(page_content, encoding="utf-8")
        print(f"Generated: site/{slug}.md")

    # Generate index
    index_content = generate_index(registry, book_data)
    (SITE_DIR / "index.md").write_text(index_content, encoding="utf-8")
    print("Generated: site/index.md")

    # Generate books page
    books_content = generate_books_page(book_data)
    (SITE_DIR / "books.md").write_text(books_content, encoding="utf-8")
    print("Generated: site/books.md")

    print("\nBuild complete!")


if __name__ == "__main__":
    main()
