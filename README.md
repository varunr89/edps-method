# EDPS Method

A research-backed system for extracting lasting knowledge from foundational texts. Combines spaced repetition, active recall, dual coding, and AI-assisted content generation.

**[View the methodology](https://varunr89.github.io/edps-method/methodology.html)** | **[See the dashboard](https://varunr89.github.io/edps-method/)**

---

## Prerequisites

- **Python 3.11+**
- **VS Code** with GitHub Copilot subscription (for LLM access)
- **[NotebookLM](https://notebooklm.google.com/)** account (free) — for generating audio overviews
- A plain text file of the book (e.g., from [Project Gutenberg](https://www.gutenberg.org/))

> **No GitHub Copilot?** See [Azure Fallback](#azure-fallback) or [Manual Workflow](#manual-workflow-no-api) below.

---

## Quick Start

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/edps-method.git
cd edps-method
```

This gives you the complete system: CLI tools, VS Code extension, and book structure.

### 2. Install the CLI

```bash
cd tools
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ..
```

The CLI (`edps`) automates ingestion, content generation, and progress tracking.

### 3. Install the VS Code extension

```bash
code --install-extension edps-llm-bridge/dist/edps-llm-bridge.vsix
```

This extension creates a local HTTP bridge between the CLI and VS Code's Language Model API (Copilot). It provides access to GPT-4o, Claude Sonnet, and Gemini with large context windows (128K-1M tokens).

**Verify installation:** Open VS Code, press `Cmd+Shift+P`, type "EDPS: LLM Bridge Status". You should see the server running.

### 4. Configure the CLI

```bash
mkdir -p ~/.edps
cat > ~/.edps/config.yaml << 'EOF'
provider: "vscode"

vscode:
  discovery_file: "~/.edps/server.json"
  timeout: 30

models:
  summary: "gemini-2.0-flash"
  quiz: "claude-sonnet-4"
  evaluation: "gpt-4o"

defaults:
  temperature: 0.3
  max_tokens: 4096
  confirm_before_call: true
EOF
```

The CLI will connect to VS Code's LLM bridge automatically when you run commands.

### 5. Add your first book

Edit `books/_registry.yaml` to add your book:

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

The **slug** is a URL-safe identifier used for folder names and commands.

### 6. Download and ingest

```bash
# Download raw text (filename must match slug)
mkdir -p books_raw
curl -o books_raw/wealth-of-nations.txt \
  https://www.gutenberg.org/cache/epub/3300/pg3300.txt

# Ingest: validates registry, chunks by chapter, creates section structure
edps ingest wealth-of-nations
```

This creates `books/wealth-of-nations/` with:
- `sections.yaml` — section boundaries and metadata
- `sections/001/`, `sections/002/`, etc. — one folder per section
- `EDPS-wealth-of-nations-001.txt`, etc. — source text files (ready for NotebookLM upload)

### 7. Generate AI content

```bash
# Generate all content types for all sections
edps generate wealth-of-nations

# Or generate specific types
edps generate wealth-of-nations 001 --type summary
edps generate wealth-of-nations 001 --type quiz
```

For each section, this creates:
- `summary.md` — AI-generated summary with key terms, argument structure, modern applications
- `quiz.md` — 8 questions (5 recall, 2 explain, 1 apply)
- `podcast.md` — Placeholder pointing to NotebookLM
- `recall.md` — Template for your memory notes

### 8. Start learning

```bash
edps run wealth-of-nations
```

This opens an interactive menu to continue generating content or review progress.

---

## The Daily Workflow

For each section, follow this 30-45 minute loop:

| Step | What to do | Time | File |
|------|------------|------|------|
| **1. Listen** | Upload `EDPS-{slug}-{id}.txt` to [NotebookLM](https://notebooklm.google.com/) and generate an audio overview | 8-12 min | Source file |
| **2. Recall** | Write what you remember — **without looking** | 5 min | `recall.md` |
| **3. Read** | Consult the summary, fill gaps in your recall notes | 10-20 min | `summary.md` |
| **4. Quiz** | Answer questions from memory | 5-10 min | `quiz.md` |
| **5. Commit** | Commit your work — AI evaluates automatically | 2 min | `progress.yaml` |

### Example: Filling in recall.md

```markdown
## From Memory (before re-reading)

1. Division of labor is critical to increase of wealth of a nation.
2. DoL leads to productivity increase by specialization, reduced context switching, and automation.
3. Pin manufacturing: specialized workers produce 240x more pins than generalists.
4. Modern parallel: AI training requires specialized skills (Andrew Ng's observation).
5. Uncertain: Can division of labor apply to farming given seasonality constraints?
```

---

## AI Evaluation

When you commit filled recall and quiz files, the pre-commit hook automatically:

1. Detects completed homework (all `[Your answer]` placeholders filled)
2. Runs AI evaluation against the source text (~15 seconds)
3. Appends detailed feedback to your files
4. Updates `progress.yaml` with scores

### Setup (one-time)

```bash
edps init-hooks
```

### How it works

```bash
git add books/wealth-of-nations/sections/001/recall.md
git add books/wealth-of-nations/sections/001/quiz.md
git commit -m "Complete section 001"
# AI evaluates, appends feedback, updates progress.yaml automatically
```

### LLM Council (Multi-Model Evaluation)

For fair evaluation, the system uses a 3-stage council with diverse models:

```
Stage 1: Independent Evaluation
  GPT-4o ──────────────▶ Answer A
  Claude Sonnet ───────▶ Answer B
  Gemini ──────────────▶ Answer C

Stage 2: Cross-Review
  Each model reviews the other two answers

Stage 3: Chair Synthesis
  GPT-4o (chair) synthesizes all answers + reviews → Final Score
```

Configure the council in `~/.edps/config.yaml`:

```yaml
council:
  enabled: true
  tasks: ["evaluation"]
  models: ["gpt-4o", "claude-sonnet-4", "gemini-2.0-flash"]
  chair: "gpt-4o"
  stages: 3  # Use 1 to disable council
```

### Manual evaluation

```bash
edps eval wealth-of-nations 001  # Evaluate specific section
edps sync wealth-of-nations      # Sync progress without AI evaluation
```

---

## Weekly Synthesis

Every 8-12 sections, pause to consolidate learning:

```bash
cp books/wealth-of-nations/weekly/_template.md \
   books/wealth-of-nations/weekly/$(date +%Y-%m-%d).md
```

Fill in:
- Top 3 claims from this week
- How they connect to each other
- One strong objection + your response
- One modern application (specific, not generic)
- Gaps or questions for next week

---

## Book Completion

When you finish all sections, complete these final outputs in `outputs/`:

| Output | Who writes | Purpose |
|--------|------------|---------|
| `one-pager.md` | You | Distill the book to exactly 10 sentences |
| `modern-mapping.md` | You | Map 5+ concepts to today's world |
| `teachable-outline.md` | AI (you refine) | 60-minute lesson plan |
| `question-bank.md` | AI (you review) | 25 short-answer + 5 essay questions |

### Spaced Review (2 weeks later)

1. Re-read your `one-pager.md`
2. Ask: *"If I had to teach this book in one hour, what would I emphasize?"*
3. Update if your thinking has evolved
4. Set status to `completed` in `_registry.yaml`

---

## Commands Reference

| Command | Purpose |
|---------|---------|
| `edps ingest {slug}` | Parse raw text, create sections (validates registry) |
| `edps generate {slug} [section-id]` | Generate AI content (summaries, quizzes, templates) |
| `edps run {slug}` | Interactive workflow menu |
| `edps eval {slug} {section-id}` | Manual AI evaluation |
| `edps sync {slug}` or `--all` | Update progress.yaml from homework files |
| `edps init-hooks` | Install pre-commit hook for auto-evaluation |
| `edps version` | Show version |

---

## Configuration

### VS Code LLM Bridge (Primary)

The extension runs automatically when VS Code starts. It:
- Creates an HTTP server on a dynamic port
- Writes discovery info to `~/.edps/server.json`
- Shuts down after 10 minutes of idle time

Check status: `Cmd+Shift+P` → "EDPS: LLM Bridge Status"

### Azure Fallback

If VS Code isn't running, the CLI falls back to Azure AI Foundry:

```yaml
# Add to ~/.edps/config.yaml
azure:
  endpoint: "https://your-endpoint.services.ai.azure.com/"
  api_key: "${AZURE_AI_KEY}"  # Uses environment variable
  model: "claude-sonnet-4-20250514"
```

```bash
export AZURE_AI_KEY="your-api-key-here"
```

### Model Selection

Configure which model handles each task:

```yaml
models:
  summary: "gemini-2.0-flash"    # Large context window for long sections
  quiz: "claude-sonnet-4"        # High quality question generation
  evaluation: "gpt-4o"           # Strong analytical reasoning
  claims_synthesis: "gpt-4o"     # Cross-section analysis
```

---

## Repository Structure

```
edps-method/
├── books/
│   ├── _registry.yaml              # Master list of all books
│   └── wealth-of-nations/
│       ├── meta.yaml               # Book metadata
│       ├── sections.yaml           # Section breakdown
│       ├── progress.yaml           # Your progress tracking
│       ├── outputs/                # Book-level final outputs
│       │   ├── one-pager.md        # 👤 You write
│       │   ├── modern-mapping.md   # 👤 You write
│       │   ├── teachable-outline.md # 🤖 AI-drafted
│       │   └── question-bank.md    # 🤖 AI-curated
│       ├── weekly/                 # Weekly synthesis notes
│       └── sections/
│           └── 001/
│               ├── EDPS-wealth-of-nations-001.txt  # Source text
│               ├── summary.md      # 🤖 AI-generated
│               ├── podcast.md      # Placeholder (use NotebookLM)
│               ├── quiz.md         # 🤖 AI-generated
│               └── recall.md       # 👤 Your notes
├── books_raw/                      # Raw .txt files for ingestion
├── edps-llm-bridge/                # VS Code extension (LLM bridge)
│   ├── dist/edps-llm-bridge.vsix   # Pre-built extension
│   └── src/                        # Extension source code
├── tools/                          # CLI source code
│   └── edps/
│       ├── commands/               # CLI commands
│       ├── core/                   # LLM client, chunker, etc.
│       └── prompts/                # AI prompt templates
├── templates/                      # Reference templates
├── docs/                           # Additional documentation
└── site/                           # Generated dashboard (don't edit)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         EDPS CLI (Python)                        │
│  edps ingest | generate | eval | sync | run                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
┌─────────────────────┐          ┌─────────────────────┐
│  VS Code Extension  │          │   Azure AI Foundry  │
│  (edps-llm-bridge)  │          │   (fallback)        │
│  HTTP: localhost    │          └─────────────────────┘
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  vscode.lm API      │
│  GPT-4o, Claude,    │
│  Gemini (via        │
│  Copilot)           │
└─────────────────────┘
```

---

## Troubleshooting

### "Discovery file not found"

VS Code extension isn't running. Open VS Code and check:
- Extension is installed: `Cmd+Shift+X` → search "EDPS"
- Server is running: `Cmd+Shift+P` → "EDPS: LLM Bridge Status"

### "Rate limited by VS Code"

Wait a moment and retry. The extension uses Copilot's rate limits.

### "Slug not found in registry"

Add the book to `books/_registry.yaml` before running `edps ingest`.

### Pre-commit hook not running

```bash
edps init-hooks  # Reinstall hooks
```

### Python 3.11+ not found

```bash
brew install python@3.11  # macOS
# Then use: python3.11 -m venv .venv
```

---

## Manual Workflow (No API)

If you don't have API access, copy prompts into ChatGPT or Claude:

1. **Setup structure manually:**
   ```bash
   mkdir -p books/my-book/sections/001
   # Copy chapter text to: EDPS-my-book-001.txt
   ```

2. **Generate content manually:**
   - Copy prompt from `tools/edps/prompts/summary.txt`
   - Paste into ChatGPT/Claude with your source text
   - Save output as `summary.md`
   - Repeat for `quiz.txt` → `quiz.md`

3. **Create recall template:**
   ```bash
   cp templates/phase2_recall.md books/my-book/sections/001/recall.md
   ```

4. **Follow daily workflow** — listen, recall, read, quiz, track.

---

## How the Dashboard Updates

```
You commit          GitHub Actions         Dashboard updates
progress.yaml  →  build_index.py   →   your-username.github.io/edps-method
```

### Enable GitHub Pages (one-time)

1. Go to **Settings → Pages**
2. Set Source: **GitHub Actions**
3. Push to `main` — workflow deploys automatically

---

## License

MIT
