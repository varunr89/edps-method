# EDPS Automation Script Design

> Design document for automating the EDPS Method workflow
> Created: 2025-12-21

---

## Overview

This document describes the design for `edps`, a CLI tool that automates the artifact generation for the EDPS Method. The tool handles book ingestion, AI-generated content creation, and human template scaffolding.

**Goals:**
- Automate repetitive preparation work (chunking, summaries, podcasts, quizzes)
- Maintain human control over all LLM calls (confirm before execute)
- Create templates for human-written artifacts (recall, weekly synthesis)
- Track progress and costs transparently

**Non-goals (v1):**
- PDF parsing (require pre-converted `.txt`)
- TTS audio generation (use NotebookLM manually)
- Spaced repetition scheduling

---

## Command Structure

### Commands

| Command | Purpose | Output |
|---------|---------|--------|
| `edps init` | Configure Azure credentials | `~/.edps/config.yaml` |
| `edps ingest <book>` | Parse text, chunk sections, extract structure | `sections.yaml`, `sections/*/source.txt` |
| `edps generate <book> [section]` | Generate AI content | `summary.md`, `podcast.md`, `quiz.md` |
| `edps template <book> [section]` | Create human templates | `recall.md`, `quiz-answers.md` |
| `edps run <book>` | Interactive runner (guides through workflow) | Calls above commands |

### File Structure

```
tools/edps/
├── cli.py                 # Entry point (typer/click)
├── commands/
│   ├── init.py            # edps init
│   ├── ingest.py          # edps ingest <book>
│   ├── generate.py        # edps generate <book> [section]
│   ├── template.py        # edps template <book>
│   └── run.py             # edps run <book> (interactive)
├── core/
│   ├── llm.py             # Azure AI Foundry client wrapper
│   ├── chunker.py         # Hybrid chunking logic
│   ├── prompts.py         # Prompt template loader
│   └── validator.py       # Source-match validation
├── prompts/               # Prompt text files
│   ├── summary.txt
│   ├── podcast.txt
│   ├── quiz.txt
│   ├── claims_section.txt
│   └── claims_book.txt
└── config.py              # Settings management
```

---

## LLM Integration

### Azure AI Foundry Configuration

**Global config:** `~/.edps/config.yaml`

```yaml
azure:
  endpoint: "https://<resource>.services.ai.azure.com"
  api_key: "${AZURE_AI_API_KEY}"
  model: "claude-sonnet-4-20250514"

models:
  # Per-task model overrides for cost optimization
  chunking: "claude-sonnet-4-20250514"
  summary: "claude-sonnet-4-20250514"
  podcast: "claude-sonnet-4-20250514"
  quiz: "claude-haiku-3-5"
  claims_synthesis: "claude-sonnet-4-20250514"

defaults:
  temperature: 0.3
  max_tokens: 4096
  confirm_before_call: true
  cost_warning_threshold: 0.50
```

**Per-book override:** `books/<book>/.edps.yaml` can override defaults.

### SDK

Use `azure-ai-inference` package:

```python
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

client = ChatCompletionsClient(
    endpoint=config.azure.endpoint,
    credential=AzureKeyCredential(config.azure.api_key)
)
```

---

## Chunking Strategy

### The Problem

Books like Wealth of Nations (~390,000 words) exceed Claude's context window (~150k words effective). We cannot send the full text for structure detection.

### Solution: Hybrid Cascade

The chunker tries methods in order, falling back if one fails:

```
1. External Metadata (fastest, free)
   ├── Query Gutenberg/Wikipedia for known book structure
   ├── Fuzzy-match chapter titles to find positions in text
   └── If found → use as section boundaries

2. Regex Pattern Matching (fast, free)
   ├── Scan for patterns: "CHAPTER", "BOOK", "Part", "§"
   ├── Split on markers
   └── If >80% chapters detected → use as boundaries

3. Sliding Window (robust, costs tokens)
   ├── Split into 10k word chunks with 500 word overlap
   ├── Ask Claude: "What chapters are in this chunk?"
   ├── Merge overlapping results
   └── Use merged TOC as boundaries

4. Human Fallback
   └── If all fail, prompt user to manually mark sections
```

### Section Boundary Output

After chunking, `sections.yaml` contains:

```yaml
sections:
  - id: "001"
    title: "Division of Labor: The Pin Factory"
    location: "Book I, Chapter 1"
    start_byte: 0
    end_byte: 14523
    word_count: 2341
```

---

## Claims Generation

### Bottom-Up Approach

Claims are derived from actual section text, not inferred from titles.

```
Phase 1: Extract Section Chunks
├── Use chunking strategy to find boundaries
├── Extract source.txt for each section
└── No claims generated yet

Phase 2: Section-Level Claims
├── For each section, send source.txt to Claude
├── Prompt: "What are the 2-3 core claims in this section?"
├── Store claims in summary.md
└── Output: section-level claims embedded in summaries

Phase 3: Book-Level Claims (after all sections done)
├── Collect all section-level claims
├── Send just the claims (not full text) to Claude
├── Prompt: "Synthesize into 5-9 book-level claims"
└── Output: claims-map.md with book-level claims
```

This ensures:
- Claims come from actual content, not guessed from titles
- Each claim traces back to specific sections
- Book-level claims are generated last (no drift)

---

## Confirm-Before-Execute Pattern

**Default behavior:** Every LLM call shows a preview and requires confirmation.

### Single Call Confirmation

```
┌─────────────────────────────────────────────────────────┐
│  Section 001: Division of Labor - The Pin Factory       │
├─────────────────────────────────────────────────────────┤
│  Action:     Generate summary.md                        │
│  Input:      source.txt (2,341 words)                   │
│  Prompt:     prompts/summary.txt (847 tokens)           │
│  Est. input: ~3,200 tokens                              │
│  Est. cost:  $0.0096                                    │
├─────────────────────────────────────────────────────────┤
│  [Enter] Proceed  [s] Skip  [v] View prompt  [q] Quit   │
└─────────────────────────────────────────────────────────┘
```

### Batch Confirmation

```
┌─────────────────────────────────────────────────────────┐
│  Batch: Generate summaries for 19 sections              │
├─────────────────────────────────────────────────────────┤
│  Total input:  ~58,400 tokens                           │
│  Est. output:  ~12,000 tokens                           │
│  Est. cost:    $0.21                                    │
│  Time:         ~4 minutes                               │
├─────────────────────────────────────────────────────────┤
│  [Enter] Proceed  [1] One-by-one  [v] View list  [q]    │
└─────────────────────────────────────────────────────────┘
```

### Override Flags

- `--yes` / `-y` — Skip confirmations (for scripting)
- `--one-by-one` — Force individual confirmations in batch mode
- `--dry-run` — Show what would happen without any API calls

---

## Interactive Runner

`edps run <book>` provides a guided workflow.

### Main Menu

```
$ edps run wealth-of-nations

╔═══════════════════════════════════════════════════════════╗
║  EDPS Method - The Wealth of Nations                      ║
║  Adam Smith, 1776                                         ║
╠═══════════════════════════════════════════════════════════╣
║  Status: 19 sections identified, 3 summaries generated    ║
╚═══════════════════════════════════════════════════════════╝

What would you like to do?

  [1] Continue generating (sections 004-019)
  [2] Review existing outputs
  [3] Regenerate a specific section
  [4] Generate human templates (recall.md, quiz-answers.md)
  [5] Run validation checks
  [6] View cost summary so far
  [q] Quit

> _
```

### State Detection

Runner derives state from existing files:
- `sections.yaml` exists → ingestion complete
- `sections/001/summary.md` exists → section 001 summary done
- No separate state file (files are source of truth)

### Session Tracking

Runner tracks cumulative cost and time within a session, displayed on exit:

```
Session Summary:
  Sections processed: 5
  Tokens used: 24,500
  Cost: $0.08
  Time: 12 minutes
```

---

## Failure Modes & Mitigations

| Failure Mode | Mitigation |
|--------------|------------|
| **LLM hallucination** | Post-generation validation: fuzzy-match claims against source text. Flag sections with <50% match. |
| **Section too long** | Pre-check word count. If >8k words, split into sub-sections or summarize in two passes. |
| **API rate limits** | Exponential backoff + retry. Save after each section. Resume on failure. |
| **Cost blowup** | Token estimation before call. Warn if batch >$0.50. Confirm before execute. |
| **Encoding issues** | Normalize to UTF-8 on ingest. Log warnings for manual review. |
| **Fuzzy-match failure** | Fall back to byte-offset estimation. Flag for human review. |

---

## Output File Structure

```
books/
└── wealth-of-nations/
    ├── meta.yaml                 # Book metadata (user creates)
    ├── sections.yaml             # Section boundaries (generated)
    ├── claims-map.md             # Book-level claims (generated last)
    ├── glossary.md               # Key terms (generated)
    ├── progress.yaml             # Learning progress (user updates)
    │
    ├── sections/
    │   ├── 001/
    │   │   ├── source.txt        # Extracted chunk (generated)
    │   │   ├── summary.md        # TLDR, claims, argument (generated)
    │   │   ├── podcast.md        # Two-speaker script (generated)
    │   │   ├── quiz.md           # 8 questions (generated)
    │   │   ├── recall.md         # Template (generated), user fills
    │   │   └── quiz-answers.md   # Template (generated), user fills
    │   └── .../
    │
    ├── weekly/
    │   └── YYYY-MM-DD.md         # Weekly synthesis (template, user fills)
    │
    └── outputs/
        ├── one-pager.md          # Template (user writes)
        ├── teachable-outline.md  # AI draft, user refines
        ├── question-bank.md      # Generated from all quizzes
        └── modern-mapping.md     # Template (user writes)
```

### File Headers

Generated files include:
```markdown
<!-- Generated by EDPS v1.0 | 2025-01-15 | claude-sonnet-4-20250514 -->
```

Human template files include:
```markdown
<!-- TEMPLATE: Fill in sections below -->
```

---

## Dependencies

```
# requirements.txt
azure-ai-inference>=1.0.0
typer>=0.9.0
rich>=13.0.0
pyyaml>=6.0
tiktoken>=0.5.0
thefuzz>=0.20.0
```

| Package | Purpose |
|---------|---------|
| `azure-ai-inference` | Azure AI Foundry SDK |
| `typer` | CLI framework |
| `rich` | Terminal UI (tables, prompts, progress) |
| `pyyaml` | Config and sections.yaml parsing |
| `tiktoken` | Token estimation for cost preview |
| `thefuzz` | Fuzzy matching for chapter detection |

---

## Implementation Priority

### Phase 1: Core Pipeline
1. `edps init` — Azure config setup
2. `edps ingest` — Regex chunking only (simplest case)
3. `edps generate` — Single section, summary only
4. Confirm-before-execute pattern

### Phase 2: Full Generation
5. Podcast and quiz generation
6. Batch mode with cost estimation
7. `edps template` — Human template creation

### Phase 3: Interactive Runner
8. `edps run` — Main menu and state detection
9. Validation checks (source-match)
10. Cost tracking across sessions

### Phase 4: Robust Chunking
11. External metadata lookup (Gutenberg/Wikipedia)
12. Sliding window fallback
13. Claims-map synthesis (bottom-up)

---

## Open Questions

1. **Glossary generation** — Generate per-section or one pass at the end?
2. **Podcast length control** — How to ensure scripts hit 8-12 minute target?
3. **Weekly synthesis triggers** — Auto-detect when to prompt for weekly synthesis?

---

*Ready for implementation.*
