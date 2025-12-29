# Web UI Design

**Date:** 2025-12-29
**Status:** Approved
**Goal:** Replace Obsidian-based workflow with a local web UI for reading, writing, and receiving feedback—all in the browser.

## Problem

Current workflow has friction:
1. **Context switching** — jumping between Obsidian (editing), terminal (CLI), and browser (progress site)
2. **Feedback readability** — injected `<details>` blocks in markdown don't render as nicely as a proper UI

## Solution

A local web server (`edps run`) that provides:
- Form-based UI per book with all sections
- Structured inputs for recall and quiz
- Auto-save to existing markdown files
- Explicit evaluation with rich feedback display
- Warm scholarly aesthetic matching the public site

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       edps run                               │
│                    (localhost:8000)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   FastAPI Backend                                            │
│   ├── Routes (HTML responses)                                │
│   │   ├── GET  /                    → Book list              │
│   │   ├── GET  /book/{slug}         → Book overview          │
│   │   └── GET  /book/{slug}/{id}    → Section workspace      │
│   │                                                          │
│   ├── HTMX Endpoints (partial HTML)                          │
│   │   ├── POST /book/{slug}/{id}/save      → Auto-save       │
│   │   └── POST /book/{slug}/{id}/evaluate  → Get feedback    │
│   │                                                          │
│   └── File I/O                                               │
│       ├── Reads: recall.md, quiz.md, summary.md, podcast.md  │
│       └── Writes: recall.md, quiz.md (with feedback)         │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│   Frontend (server-rendered)                                 │
│   ├── Jinja2 templates                                       │
│   ├── Tailwind CSS (CDN)                                     │
│   ├── HTMX for reactivity                                    │
│   └── ~50 lines vanilla JS for hover tooltips                │
└─────────────────────────────────────────────────────────────┘
```

**Key principle:** Server renders complete HTML pages. HTMX handles partial updates without full page reloads. No client-side routing, no JavaScript framework.

## File Structure

```
tools/edps/
├── commands/
│   └── run.py            # Updated to launch web server
├── web/
│   ├── app.py            # FastAPI application
│   ├── routes.py         # Route handlers
│   ├── templates/        # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html    # Book list
│   │   ├── book.html     # Section progress
│   │   └── section.html  # Tabbed workspace
│   └── static/
│       ├── styles.css    # Custom styles (extends Tailwind)
│       └── app.js        # Minimal JS for tooltips
└── ...
```

## Navigation Structure

### Level 1: Book List (`/`)

List of all books from registry with status indicators.

```
┌──────────────────────────────────────────────────────────────────┐
│  EDPS Reading Dashboard                                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  IN PROGRESS                                                     │
│  ───────────────────────────────────────────────────────────     │
│  📖 The Wealth of Nations          3/32 sections                 │
│                                                                  │
│  PLANNED                                                         │
│  ───────────────────────────────────────────────────────────     │
│  📚 Capital, Vol. 1                0/50 sections                 │
│  📚 The General Theory             0/24 sections                 │
│  ...                                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Level 2: Book Page (`/book/{slug}`)

All sections with progress indicators.

```
┌──────────────────────────────────────────────────────────────────┐
│  ← All Books                                                     │
│                                                                  │
│  THE WEALTH OF NATIONS                                           │
│  Adam Smith · 1776                                               │
│                                                                  │
│  Progress: ████████░░░░░░░░░░░░░░░░░░░░░░░░  3/32 sections      │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SECTIONS                                                        │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  ✓  001  Division of Labor                    7/8  ████████░    │
│  ✓  002  Causes of Division of Labor          7/8  ████████░    │
│  ◐  003  Division Limited by Market           –    In progress  │
│  ○  004  Origin of Money                      –    Not started  │
│  ...                                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Level 3: Section Workspace (`/book/{slug}/{id}`)

Tabbed interface following the EDPS learning flow.

```
┌──────────────────────────────────────────────────────────────────┐
│  ← Wealth of Nations                          Section 3 of 32    │
│  "Of the Extent of the Market"                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┬─────────┬─────────┬─────────┐                      │
│  │ Summary │ Recall  │  Quiz   │ Podcast │                      │
│  └─────────┴─────────┴─────────┴─────────┘                      │
│                                                                  │
│  (Tab content renders here based on selection)                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Tab states:**
- Grayed out if file doesn't exist yet
- Checkmark badge if completed
- Active tab highlighted with gold underline

## Tab Content Details

### Summary Tab (read-only)

Renders `summary.md` as styled HTML with collapsible sections:
- TLDR (blockquote style)
- Key Terms (definition list)
- Argument Structure (numbered with logical connectors)
- Modern Application (collapsible)
- Source Pointers (collapsible)

### Recall Tab (form + feedback)

Structured inputs mapping to `recall.md`:

| Field | Input Type |
|-------|------------|
| From Memory (5 points) | 5 separate textareas |
| After Reading | Larger textarea |
| Score | Radio buttons styled as pills (0-5) |
| Confidence | Radio buttons (Low/Medium/High) |
| One Sentence Summary | Single line input |

After evaluation: Feedback summary panel appears showing per-point assessment.

### Quiz Tab (form + feedback)

Structured inputs mapping to `quiz.md`:

| Question Type | Input Type |
|---------------|------------|
| MCQ (select one) | Radio buttons |
| MCQ (select multiple) | Checkboxes |
| MCQ (select none valid) | Radio + "None" option |
| Prose | Textarea |

After evaluation:
- Inline error highlights in prose answers (wavy underline)
- Hover reveals tooltip with feedback
- Thematic insights panel below
- Tutor's note in collapsible section

### Podcast Tab (read-only)

- Audio player if file exists in `outputs/`
- Dialogue script rendered with speaker labels

## Data Flow

### Page Load

```
GET /book/wealth-of-nations/003
     │
     ▼
Server reads from books/wealth-of-nations/sections/003/:
  ├── summary.md   → parse, render as HTML
  ├── recall.md    → extract existing answers into form fields
  ├── quiz.md      → extract questions + any existing answers
  └── podcast.md   → render as readable script
     │
     ▼
Return fully rendered page with pre-populated forms
```

### Auto-Save

```
User types in textarea
     │
     ▼ (5 seconds of no typing, batches multiple fields)
HTMX POST /book/wealth-of-nations/003/save
     │
     ▼
Server:
  1. Receives { tab: "recall", fields: {...} }
  2. Reads current markdown file
  3. Updates specific fields
  4. Writes back to file
  5. Returns "Saved ✓" indicator
     │
     ▼
HTMX swaps indicator → user sees confirmation briefly
```

### Evaluation

```
User clicks [ Get Feedback ]
     │
     ▼
HTMX POST /book/wealth-of-nations/003/evaluate
     │ (shows loading spinner)
     ▼
Server:
  1. Calls existing evaluate_section() from evaluation.py
  2. LLM returns structured feedback JSON
  3. Renders feedback as HTML:
     - Answers with inline <mark> spans for errors
     - Summary panel with thematic insights
  4. Also writes feedback back to markdown files
     │
     ▼
HTMX swaps in:
  - Updated form with error highlights
  - Summary panel slides in
```

## Feedback Display

### Inline Error Highlights

Errors in prose answers shown with wavy underline:

```html
<span class="answer-text">
  The division of labor causes
  <mark class="error" data-feedback="Missing mechanism...">
    higher productivity
  </mark>
  through specialization.
</span>
```

On hover: tooltip appears with:
- Error type (e.g., "Incomplete", "Inaccurate")
- Detailed feedback text

### Summary Panel

Appears below the form after evaluation:

```
┌─ Thematic Insights ─────────────────────────────────────────┐
│  Source Mastery: Strong grasp of price theory               │
│  Reasoning: Good counterfactual thinking                    │
│  Writing: Consider more precise language                    │
│                                                             │
│  Tutor's Note:                                              │
│  "You've understood the core mechanism well..."             │
└─────────────────────────────────────────────────────────────┘
```

## Visual Design System

Extends the existing public site aesthetic:

### Typography

| Use | Font |
|-----|------|
| Headings | Crimson Pro (serif) |
| Body text | Crimson Pro |
| Form inputs | Crimson Pro, lighter weight |
| Scores/stats | JetBrains Mono (monospace) |

### Colors

| Role | Value | Use |
|------|-------|-----|
| Background | `#FAF8F5` | Page background |
| Surface | `#FFFFFF` | Cards, inputs |
| Text | `#3D3229` | Primary text |
| Muted | `#8B7355` | Secondary text |
| Accent | `#B8860B` | Progress bars, active states |
| Success | `#5B7C5B` | Completed indicators |
| Error | `#A65D57` | Inline error marks |

### Texture & Atmosphere

- Subtle paper texture on background (CSS noise)
- Soft warm-tinted shadows on cards
- Thin gold accent lines as dividers
- Smooth tab underline animation on switch

**Mood:** Working at a mahogany desk in a sunlit study.

## CLI Integration

### Updated Command

```bash
$ edps run                              # Launch at localhost:8000
$ edps run --port 8080                  # Custom port
$ edps run --book wealth-of-nations     # Open directly to book
$ edps run --no-browser                 # Don't auto-open browser
```

### Existing Commands

All unchanged—can still use CLI for scripting:

```bash
$ edps init <book>
$ edps generate <book> <id>
$ edps eval <book> <id>
```

### Workflow

Primary workflow becomes:
1. `edps run`
2. Work entirely in browser
3. Files auto-save to markdown
4. Git commit when done (hooks still work)

Hybrid option: Edit in Obsidian OR browser—both read/write same files.

## Dependencies

New packages to add:

```
fastapi
uvicorn
jinja2
python-multipart  # for form handling
```

HTMX and Tailwind loaded from CDN (no build step).

## Future Enhancements (not in v1)

- File watching: auto-refresh browser when files change externally
- Keyboard shortcuts: Ctrl+Enter to evaluate, tab navigation
- Progress animations: confetti on section completion
- Dark mode toggle

## Success Criteria

1. User can complete full recall + quiz workflow without leaving browser
2. Feedback displays inline with hover tooltips
3. Auto-save works reliably with visual confirmation
4. Aesthetic matches public site (warm, scholarly)
5. Existing markdown files remain source of truth
