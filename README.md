# EDPS Method

A system for extracting lasting knowledge from important books, using spaced repetition, active recall, and AI-assisted content generation.

**[View the methodology](https://varunr89.github.io/edps-method/methodology.html)** | **[See the dashboard](https://varunr89.github.io/edps-method/)**

---

## Prerequisites

- Python 3.11+
- An API key for Claude (via [Azure AI Foundry](https://ai.azure.com/) or Anthropic)
- [NotebookLM](https://notebooklm.google.com/) account (free) — for generating audio overviews
- A plain text file of the book (e.g., from [Project Gutenberg](https://www.gutenberg.org/))

> **No API key?** You can use this system manually — see [Manual Workflow](#manual-workflow-no-api) below.

---

## Quick Start

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/edps-method.git
cd edps-method
```

### 2. Install the CLI

```bash
cd tools
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Configure your API key

```bash
mkdir -p ~/.edps
cat > ~/.edps/config.yaml << 'EOF'
azure:
  endpoint: "https://your-endpoint.services.ai.azure.com/"
  api_key: "${AZURE_AI_KEY}"
  model: "claude-sonnet-4-20250514"
EOF

export AZURE_AI_KEY="your-api-key-here"
```

### 4. Add your first book

First, add the book to the registry (`books/_registry.yaml`):

```yaml
books:
  - slug: wealth-of-nations
    title: "The Wealth of Nations"
    author: "Adam Smith"
    year: 1776
    status: planned
    priority: 1
    category: "Economics"
```

Then download and ingest:

```bash
# Download the raw text (filename must match slug)
mkdir -p books_raw
curl -o books_raw/wealth-of-nations.txt \
  https://www.gutenberg.org/cache/epub/3300/pg3300.txt

# Ingest (validates slug exists in registry)
edps ingest wealth-of-nations

# Generate AI content
edps generate wealth-of-nations
```

### 5. Start learning

```bash
edps run wealth-of-nations
```

---

## The Daily Workflow

For each section, follow this loop:

| Step | What to do | File |
|------|------------|------|
| **1. Listen** | Upload the source file to [NotebookLM](https://notebooklm.google.com/) and generate an audio overview | `sections/<id>/EDPS-<slug>-<id>.txt` |
| **2. Recall** | Write what you remember — **without looking** — in the recall template | `sections/<id>/recall.md` |
| **3. Read** | Consult the summary. Fill in gaps in your recall notes. | `sections/<id>/summary.md` |
| **4. Quiz** | Answer questions from memory. Score yourself. | `sections/<id>/quiz.md` |
| **5. Track** | Update progress and commit | `progress.yaml` |

### Updating progress (automatic)

Progress is tracked automatically via a git pre-commit hook. When you commit filled recall and quiz files, `progress.yaml` updates itself:

```bash
# One-time setup: install the pre-commit hook
edps init-hooks

# Then just commit your homework as usual
git add books/<slug>/sections/001/recall.md books/<slug>/sections/001/quiz.md
git commit -m "Complete section 001"
# progress.yaml updates automatically!
```

A section is marked complete when:
- All `[Your answer]` placeholders are filled in `recall.md`
- A score line exists (e.g., `**My score**: [4] / 5`)
- All `**Answer:**` sections are filled in `quiz.md`
- A total line exists (e.g., `**Total: 7 / 8**`)

**Manual sync** (if needed):

```bash
edps sync wealth-of-nations      # Sync one book
edps sync --all                  # Sync all books
```

---

## Weekly Synthesis

Every 8-12 sections, pause to consolidate your learning:

| Step | What to do | File |
|------|------------|------|
| **1. Review** | Re-read your recall notes from the week | `sections/*/recall.md` |
| **2. Synthesize** | Copy the template and write connections | `weekly/YYYY-MM-DD.md` |
| **3. Quiz** | Answer random questions from past sections | Mixed `quiz.md` files |

### Creating a weekly synthesis

```bash
# Copy the template
cp books/<slug>/weekly/_template.md books/<slug>/weekly/$(date +%Y-%m-%d).md

# Edit, then commit
git add books/<slug>/weekly/
git commit -m "Weekly synthesis: sections 001-012"
```

**Time estimate:** 45-60 minutes

---

## Book Completion

When you've finished all sections, complete these final outputs in `outputs/`:

| Output | What to do | File |
|--------|------------|------|
| **One-Pager** | Distill the book to exactly 10 sentences | `outputs/one-pager.md` |
| **Modern Mapping** | Map 5+ concepts to today's world | `outputs/modern-mapping.md` |
| **Teachable Outline** | Review/refine the AI-drafted lesson plan | `outputs/teachable-outline.md` |
| **Question Bank** | Review the curated questions | `outputs/question-bank.md` |

The `one-pager.md` and `modern-mapping.md` are templates you fill in yourself.
The `teachable-outline.md` and `question-bank.md` are AI-generated drafts to refine.

---

## Spaced Review (2 Weeks Later)

Two weeks after completing a book:

1. Re-read your `outputs/one-pager.md`
2. Ask yourself: *"If I had to teach this book in one hour, what would I emphasize?"*
3. Update your one-pager if your thinking has evolved
4. Update `_registry.yaml` to mark the book as `completed`

---

## How the Dashboard Updates

When you push changes, GitHub Actions automatically rebuilds your public dashboard.

```
You commit          GitHub Actions         Dashboard updates
progress.yaml  -->  build_index.py   -->   your-username.github.io/edps-method
```

### Enable GitHub Pages (one-time setup)

1. Go to your fork's **Settings → Pages**
2. Under "Build and deployment", set:
   - **Source**: GitHub Actions
3. Push any change to `main` — the workflow will deploy automatically
4. Your dashboard will be live at `https://<your-username>.github.io/edps-method/`

### What gets displayed

- Books from `books/_registry.yaml` (title, author, status)
- Progress percentage calculated from `progress.yaml`
- Section completion counts

### Adding a book to the dashboard

Add an entry to `_registry.yaml`:

```yaml
books:
  - slug: leviathan
    title: "Leviathan"
    author: "Thomas Hobbes"
    year: 1651
    status: in_progress
    priority: 1
    category: "Political Philosophy"
```

The site regenerates on every push to `main`.

---

## Manual Workflow (No API)

If you don't have an API key, you can still use this system by copying prompts into ChatGPT or Claude.

### 1. Set up the book structure manually

```bash
mkdir -p books/my-book/sections/001
# Copy your chapter text into (naming makes it easy to upload to NotebookLM):
# books/my-book/sections/001/EDPS-my-book-001.txt
```

### 2. Generate content manually

Copy the prompt from `tools/edps/prompts/summary.txt` and paste it into ChatGPT/Claude, along with your source text. Save the output as `summary.md`.

Repeat for `quiz.txt` → `quiz.md`.

### 3. Create recall template

Copy `templates/phase2_recall.md` to `books/my-book/sections/001/recall.md`.

### 4. Follow the daily workflow

The rest of the process is the same — listen (via NotebookLM), recall, read, quiz, track.

---

## Repository Structure

```
edps-method/
├── books/
│   ├── _registry.yaml              # Master list of all books
│   └── wealth-of-nations/          # Each book has its own folder
│       ├── meta.yaml               # Book metadata
│       ├── sections.yaml           # Section breakdown
│       ├── progress.yaml           # Your progress tracking
│       ├── outputs/                # Book-level outputs
│       │   ├── one-pager.md        # 👤 You write (10 sentences)
│       │   ├── modern-mapping.md   # 👤 You write (5+ domains)
│       │   ├── teachable-outline.md # 🤖 AI-drafted lesson plan
│       │   └── question-bank.md    # 🤖 AI-curated questions
│       ├── weekly/                 # Weekly synthesis notes
│       │   ├── _template.md        # Copy this for each synthesis
│       │   └── 2025-01-01.md       # Your dated syntheses
│       └── sections/
│           └── 001/
│               ├── EDPS-wealth-of-nations-001.txt  # Source text
│               ├── summary.md      # 🤖 AI-generated
│               ├── podcast.md      # Placeholder (use NotebookLM)
│               ├── quiz.md         # 🤖 AI-generated
│               └── recall.md       # 👤 Your recall notes
├── books_raw/                      # Raw .txt files for ingestion
├── templates/                      # Reference templates
├── tools/                          # CLI and build scripts
└── site/                           # Generated dashboard (don't edit)
```

---

## License

MIT
