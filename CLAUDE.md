# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The EDPS Method is a research-backed reading system for extracting lasting knowledge from foundational texts. Named after four cognitive scientists (Ebbinghaus, Dunlosky, Paivio, Sweller), it combines spaced repetition, active recall, dual coding, and cognitive load management.

This repository serves two purposes:
1. **Data store**: YAML files tracking book metadata, sections, and progress
2. **Static site generator**: Python script that builds GitHub Pages for public accountability

## Build Commands

```bash
# Generate the static site (outputs to site/)
python tools/build_index.py

# Requires pyyaml
pip install pyyaml
```

The GitHub Actions workflow (`.github/workflows/pages.yml`) automatically runs `build_index.py` on push to main and deploys to GitHub Pages.

## Architecture

### Data Layer (YAML)

```
books/
├── _registry.yaml          # Master list of all books with metadata
└── {book-slug}/
    ├── meta.yaml           # Book-specific metadata
    ├── sections.yaml       # Section breakdown with claims and priorities
    └── progress.yaml       # Completion tracking
```

**Registry precedence**: Fields in `_registry.yaml` override those in individual `meta.yaml` files. The registry is the source of truth for status, priority, and category.

**Section priorities**: Each section has a `priority` field (`must` or `skim`) indicating reading depth.

### Site Generator (`tools/build_index.py`)

Single-file Python script that:
1. Reads `_registry.yaml` to get the book list
2. Merges registry data with per-book YAML files
3. Generates self-contained HTML (CSS embedded, no Jekyll) into `site/`

Key functions:
- `generate_index_html()` - Main dashboard with category accordions
- `generate_book_page_html()` - Individual book progress pages
- `generate_methodology_page()` - Static "What is this?" page

### Templates

Templates in `templates/` define the markdown structure for learning artifacts:
- `summary.md` - AI-generated section summaries with TLDR, argument structure, modern applications
- `recall.md` - Memory-based notes before consulting source
- `quiz.md` - Retrieval practice questions
- `podcast.md` - Audio content structure
- `weekly-synthesis.md` - Cross-section integration notes

## Key Conventions

**Book slugs**: URL-safe identifiers (e.g., `wealth-of-nations`, `capital-vol-1`). Used as directory names and in URLs.

**Status values**: `planned`, `in_progress`, `completed`

**Claim tags**: Each section links to high-level claims (`division_of_labor`, `free_trade`, etc.) defined at the top of `sections.yaml`.

**Progress tracking**: `progress.yaml` contains a `completed_sections` list of section IDs.

## GitHub Configuration

- Repository: `https://github.com/varunr89/edps-method`
- Deployment: GitHub Pages from `site/` directory via Actions
