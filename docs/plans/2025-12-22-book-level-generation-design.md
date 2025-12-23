# Book-Level Generation Design

> Date: 2025-12-22
> Status: Approved

## Problem

The EDPS tooling (`edps generate`) only creates section-level content (summary, podcast, quiz, recall). The workflow diagram specifies book-level outputs that aren't being generated:

- `one-pager.md` — Reader-written template
- `teachable-outline.md` — AI-drafted lesson plan
- `question-bank.md` — AI-curated from all section quizzes
- `modern-mapping.md` — Reader-written template
- Weekly synthesis template

The README also only documents the daily section workflow, missing weekly synthesis, book completion, and spaced review phases.

## Solution

Extend `edps generate` to create book-level outputs in addition to section-level content.

## Directory Structure

After running `edps generate <book-slug>`:

```
books/<book-slug>/
├── meta.yaml
├── sections.yaml
├── progress.yaml
├── outputs/                          # NEW
│   ├── one-pager.md                 # 👤 Template
│   ├── teachable-outline.md         # 🤖 AI-generated
│   ├── question-bank.md             # 🤖 AI-generated
│   └── modern-mapping.md            # 👤 Template
├── weekly/                           # NEW
│   └── _template.md                 # 👤 Template to copy
└── sections/
    └── 001/
        ├── EDPS-<slug>-001.txt
        ├── summary.md
        ├── podcast.md
        ├── quiz.md
        └── recall.md
```

## Book-Level Templates (Reader-Written)

### `outputs/one-pager.md`

```markdown
# {Book Title}: One-Pager

> Generator: 👤 Reader-written
> Author: {Author}
> Completed: [YYYY-MM-DD]

---

## The Book in 10 Sentences

1. **The problem**: [What problem is the author solving?]
2. **Core claim #1**: [First major argument]
3. **Core claim #2**: [Second major argument]
4. **Core claim #3**: [Third major argument]
5. **The mechanism**: [Key process or causal chain]
6. **Best example**: [Most memorable illustration from the text]
7. **Limitation**: [What the author gets wrong or oversimplifies]
8. **Modern relevance**: [What this explains about today]
9. **Blind spot**: [What this does NOT explain]
10. **The one idea**: [What I'll remember in 10 years]

---

## Constraints

- Each sentence must contain a claim + implication (not just description)
- Sentence 7 must be critical
- Total length: 200-300 words max
```

### `outputs/modern-mapping.md`

```markdown
# Modern Mapping: {Book Title}

> Generator: 👤 Reader-written
> Completed: [YYYY-MM-DD]

---

## Domain 1: [e.g., Technology & Labor]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 2: [e.g., Trade & Globalization]

[Same structure]

## Domain 3: [e.g., Government & Regulation]

[Same structure]

## Domain 4: [e.g., Inequality & Distribution]

[Same structure]

## Domain 5: [e.g., Consumer Behavior]

[Same structure]

---

## Where the Book Falls Short

[What modern phenomena would surprise or confuse the author? What has changed since publication that invalidates parts of the argument?]
```

### `weekly/_template.md`

Copy of `templates/phase4_weekly-synthesis.md` content.

## Book-Level AI-Generated Content

### `outputs/teachable-outline.md`

**Input:** All section summaries concatenated + book metadata

**New prompt file:** `tools/edps/prompts/teachable-outline.txt`

**Output format:**
```markdown
# Teaching {Book Title} in 60 Minutes

> Generator: 🤖→👤 AI-drafted, reader-refined
> Generated: {date}

## Audience
[Target audience and assumed prior knowledge]

## Learning Objectives
By the end, students will be able to:
1. [Objective 1]
2. [Objective 2]
3. [Objective 3]

## Outline

### Segment 1: [Title] (10 min)
- **Key point**: [one sentence]
- **From the book**: [historical example]
- **Modern parallel**: [contemporary example]
- **Transition**: [leads to next segment]

### Segment 2: [Title] (10 min)
[Same structure]

### Segment 3: [Title] (10 min)
[Same structure]

### Segment 4: [Title] (10 min)
[Same structure]

### Segment 5: [Title] (10 min)
[Same structure]

### Segment 6: Synthesis & Discussion (10 min)
- Recap the 5 key points
- Discussion questions
- "If you remember one thing..."

## Predicted Student Questions
1. [Q] → [A]
2. [Q] → [A]
3. [Q] → [A]
4. [Q] → [A]
5. [Q] → [A]
```

### `outputs/question-bank.md`

**Input:** All section quizzes concatenated + book metadata

**New prompt file:** `tools/edps/prompts/question-bank.txt`

**Output format:**
```markdown
# Question Bank: {Book Title}

> Generator: 🤖 AI-curated
> Generated: {date}
> Sections covered: 001-0XX

---

## Short Answer (25 questions)
*Answer each in 2-3 sentences.*

1. [Question] *(Section 001)*
2. [Question] *(Section 003)*
...
25. [Question] *(Section 0XX)*

---

## Essay Prompts (5 questions)
*Answer each in 500-800 words.*

1. **Synthesis**: [Prompt requiring connections across multiple chapters]
2. **Comparison**: [Prompt comparing with another thinker/framework]
3. **Application**: [Prompt applying ideas to a modern issue]
4. **Critique**: [Prompt evaluating the author's argument]
5. **Reflection**: [Prompt: "How has this changed your thinking about...?"]
```

## Implementation Changes

### `tools/edps/commands/generate.py`

1. After generating all section content, generate book-level content
2. Create `outputs/` and `weekly/` directories
3. Generate templates for reader-written files
4. Call LLM for AI-generated files (teachable-outline, question-bank)

### New prompt files

- `tools/edps/prompts/teachable-outline.txt`
- `tools/edps/prompts/question-bank.txt`

### README.md updates

Add sections for:
1. Weekly Synthesis workflow
2. Book Completion phase
3. Spaced Review (2 weeks later)

## Generation Order

1. All section summaries (existing)
2. All section quizzes (existing)
3. All section recalls (existing)
4. Book-level templates: one-pager.md, modern-mapping.md, weekly/_template.md
5. Book-level AI content: teachable-outline.md (needs all summaries), question-bank.md (needs all quizzes)

## Skip Logic

- Skip book-level generation if `outputs/` files already exist (same as section-level)
- Allow `--type book` flag to only generate book-level content
- Allow `--type sections` flag to only generate section-level content
