# EDPS Method

Extract lasting knowledge from foundational texts using spaced repetition, active recall, and AI-assisted evaluation.

**[View methodology](https://varunr89.github.io/edps-method/methodology.html)** | **[Dashboard](https://varunr89.github.io/edps-method/)**

---

## Prerequisites

- **Python 3.11+**
- **VS Code** with GitHub Copilot (for LLM access)
- **[NotebookLM](https://notebooklm.google.com/)** (free) — generates audio overviews
- Plain text of your book (e.g., from [Project Gutenberg](https://www.gutenberg.org/))

> **No Copilot?** See [Manual Workflow](#manual-workflow-no-api) or [Azure Fallback](#azure-fallback).

---

## Quick Start

**Goal:** Get from zero to learning in 5 minutes.

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/edps-method.git
cd edps-method
```

### 2. Install CLI

```bash
cd tools
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ..
```

### 3. Install VS Code extension

```bash
code --install-extension edps-llm-bridge/dist/edps-llm-bridge.vsix
```

Verify: `Cmd+Shift+P` → "EDPS: LLM Bridge Status" → should show server running.

### 4. Configure

```bash
mkdir -p ~/.edps
cat > ~/.edps/config.yaml << 'EOF'
provider: "vscode"
vscode:
  discovery_file: "~/.edps/server.json"
  timeout: 120
models:
  summary: "gemini-3-flash"
  quiz: "claude-sonnet-4.5"
  evaluation: "gpt-5"
defaults:
  temperature: 0.3
  max_tokens: 4096
EOF
```

### 5. Add your book

Edit `books/_registry.yaml`:

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

### 6. Download and ingest

```bash
mkdir -p books_raw
curl -o books_raw/wealth-of-nations.txt \
  https://www.gutenberg.org/cache/epub/3300/pg3300.txt

edps ingest wealth-of-nations
```

### 7. Generate content

```bash
edps generate wealth-of-nations
```

Creates for each section: `summary.md`, `quiz.md`, `recall.md`, `podcast.md`.

### 8. Enable AI evaluation

```bash
edps init-hooks
```

Now when you commit completed recall/quiz files, AI evaluates your answers automatically.

### Done! Start learning

```bash
edps run wealth-of-nations
```

---

## Daily Workflow

For each section (30-45 minutes):

| Step | Action | Time | File |
|------|--------|------|------|
| 1 | **Listen** — Upload source to NotebookLM, generate audio | 8-12 min | `EDPS-{slug}-{id}.txt` |
| 2 | **Recall** — Write what you remember, without looking | 5 min | `recall.md` |
| 3 | **Read** — Check summary, fill gaps | 10-20 min | `summary.md` |
| 4 | **Quiz** — Answer from memory | 5-10 min | `quiz.md` |
| 5 | **Commit** — AI evaluates, updates scores | 2 min | `progress.yaml` |

### Example recall

```markdown
## From Memory (before re-reading)

1. Division of labor increases national wealth.
2. Specialization → productivity gains → reduced context switching.
3. Pin factory: specialists produce 240x more pins than generalists.
4. Modern parallel: AI training requires specialized skills.
5. Uncertain: Does division of labor apply to seasonal farming?
```

### How evaluation works

```bash
git add books/wealth-of-nations/sections/001/recall.md
git add books/wealth-of-nations/sections/001/quiz.md
git commit -m "Complete section 001"
# → AI evaluates answers against source text
# → Appends feedback to your files
# → Updates progress.yaml with scores
```

Or evaluate manually without committing:

```bash
edps eval wealth-of-nations 001
```

**What you get back:**

Each recall point and quiz answer receives three feedback dimensions:
- **Accuracy:** Did you capture what the source says?
- **Reasoning:** Is your logic sound?
- **Writing:** Is it clear and precise?

Plus overall thematic insights (source mastery, reasoning patterns, writing craft scores 1-5) and a tutor's note with actionable next steps.

<details>
<summary>Example evaluation output</summary>

```markdown
## AI Feedback

**Evaluated:** 2025-12-27 | **Source:** EDPS-wealth-of-nations-001.txt
**Total Score:** 6.5/8

---

### Per-Answer Analysis

#### Q1: Division of Labor (1.0/1.0) ✓

**Accuracy:** Correctly identifies that specialization increases output.
**Reasoning:** Causal chain is sound—less context switching means more throughput.
**Writing:** "240x productivity gain" is precise and memorable.

#### Q2: Market Limits (0.5/1.0) ⚠️

**Accuracy:** Partial—mentions market size but misses transportation costs.
**Reasoning:** The connection between market extent and specialization is incomplete.
**Writing:** Could be more concise; 42 words for a simple point.

---

### Thematic Insights

#### Source Mastery
You consistently nail the core mechanisms but miss qualifying conditions.
Smith's argument depends on transportation costs, which you haven't addressed.

#### Reasoning Quality
Your causal chains are sound when you build them. The gap is completeness—you
stop one step short of Smith's full argument.

#### Writing Craft
**Precision:** 4/5 | **Clarity:** 4/5 | **Economy:** 3/5

**Practice:** Cut "it is important to note that" from your vocabulary.

---

### Tutor's Note

Strong grasp of the division of labor argument—your pin factory example
shows you understand why specialization works, not just that it does.

Two things to carry forward: (1) Look for the author's qualifying conditions,
not just the main claim. Smith rarely argues absolutes. (2) Your prose is
accurate but wordy. Try rewriting each answer in half the words.

Next section covers exchange and money. Watch for how Smith connects
specialization to the need for currency—it's the logical next step from
what you've learned here.
```

</details>

### Quiz format

Quizzes have two parts:

**Part A: Multiple Choice** with three answer types:
- `one` — exactly one correct answer
- `multiple` — two or more correct (scored via F1 for partial credit)
- `none` — all options are incorrect

**Part B: Prose Questions** with four types:
- Adversarial: Challenge a claim's weakest point
- Comparative: Connect ideas across sections
- Socratic: Probe "what if" scenarios
- Synthesis: Apply concepts to modern cases

---

## Commands

| Command | Purpose |
|---------|---------|
| `edps ingest {slug}` | Parse raw text into sections |
| `edps generate {slug} [section]` | Generate summaries, quizzes, templates |
| `edps eval {slug} {section}` | Run AI evaluation |
| `edps sync {slug}` | Update progress without AI |
| `edps run {slug}` | Interactive menu |
| `edps init-hooks` | Install pre-commit hook |

---

## Weekly Synthesis

Every 8-12 sections, consolidate:

```bash
cp books/wealth-of-nations/weekly/_template.md \
   books/wealth-of-nations/weekly/$(date +%Y-%m-%d).md
```

Fill in: top 3 claims, connections between them, one objection with response, one specific modern application, gaps for next week.

---

## Book Completion

When finished, create final outputs in `outputs/`:

| File | Author | Purpose |
|------|--------|---------|
| `one-pager.md` | You | Book in 10 sentences |
| `modern-mapping.md` | You | 5+ concepts mapped to today |
| `teachable-outline.md` | AI | 60-minute lesson plan |
| `question-bank.md` | AI | 25 short-answer + 5 essay questions |

Two weeks later: re-read your one-pager, update if thinking evolved, mark `completed` in registry.

---

## Advanced Configuration

### LLM Council (Multi-Model Evaluation)

For fairer evaluation, enable the council—three models evaluate independently, then synthesize:

```yaml
# Add to ~/.edps/config.yaml
council:
  enabled: true
  tasks: ["evaluation"]
  member_roles: ["summary", "quiz", "evaluation"]
  chair_role: "evaluation"
  stages: 3  # Set to 1 to disable
```

The council resolves roles to models from your `models:` config automatically.

### Model Selection

```yaml
models:
  summary: "gemini-3-flash"       # Large context, fast
  quiz: "claude-sonnet-4.5"       # Quality questions
  evaluation: "gpt-5"             # Strong reasoning
```

### Azure Fallback

If VS Code isn't running, CLI falls back to Azure:

```yaml
azure:
  endpoint: "https://your-endpoint.services.ai.azure.com/"
  api_key: "${AZURE_AI_KEY}"
  model: "claude-sonnet-4-20250514"
```

```bash
export AZURE_AI_KEY="your-key"
```

### VS Code Extension Details

The extension:
- Creates HTTP server on dynamic port
- Writes discovery to `~/.edps/server.json`
- Runs until VS Code closes (no idle timeout)

Check status: `Cmd+Shift+P` → "EDPS: LLM Bridge Status"

---

## Repository Structure

```
edps-method/
├── books/
│   ├── _registry.yaml           # Book list
│   └── {book-slug}/
│       ├── sections.yaml        # Section metadata
│       ├── progress.yaml        # Your scores
│       ├── outputs/             # Final outputs
│       ├── weekly/              # Synthesis notes
│       └── sections/001/
│           ├── EDPS-{slug}-001.txt  # Source
│           ├── summary.md       # 🤖 Generated
│           ├── quiz.md          # 🤖 Generated
│           └── recall.md        # 👤 Your notes
├── books_raw/                   # Raw .txt files
├── edps-llm-bridge/             # VS Code extension
└── tools/                       # CLI source
```

---

## Troubleshooting

**"Discovery file not found"**
→ VS Code not running. Open VS Code, check extension status.

**"Request timed out"**
→ Increase `vscode.timeout` in config (default: 120s).

**"Slug not found in registry"**
→ Add book to `books/_registry.yaml` first.

**Pre-commit hook not running**
→ Run `edps init-hooks` to reinstall.

---

## Manual Workflow (No API)

Without API access, use ChatGPT/Claude manually:

1. Create structure: `mkdir -p books/my-book/sections/001`
2. Copy prompts from `tools/edps/prompts/` into ChatGPT with your source text
3. Save outputs as `summary.md`, `quiz.md`
4. Copy template: `cp templates/phase2_recall.md books/my-book/sections/001/recall.md`
5. Follow daily workflow manually

---

## Dashboard

```
You commit → GitHub Actions → Dashboard updates
progress.yaml    build_index.py    your-username.github.io/edps-method
```

Enable GitHub Pages: **Settings → Pages → Source: GitHub Actions**

---

## License

MIT
