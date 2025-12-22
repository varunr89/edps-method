# The EDPS Method

> **E**bbinghaus · **D**unlosky · **P**aivio · **S**weller
>
> A research-backed system for extracting lasting knowledge from important works.

---

## What Is This?

Most people read important books and forget them. This system fixes that.

The EDPS Method combines four decades of cognitive psychology research into a practical workflow:

| Researcher | Contribution | How We Use It |
|------------|--------------|---------------|
| **Hermann Ebbinghaus** (1885) | Forgetting curve, spacing effect | Spaced repetition across days/weeks |
| **John Dunlosky** (2013) | Ranked learning techniques by effectiveness | Active recall, retrieval practice |
| **Allan Paivio** (1971) | Dual coding theory | Multimodal learning (listen → write → read) |
| **John Sweller** (1988) | Cognitive load theory | Scaffolds before content |

The result: **you actually remember what you read**.

---

## Quick Start

1. **Pick a book** from the registry
2. **Listen** to the section podcast (AI-generated)
3. **Recall** — write what you remember without looking
4. **Read** selectively — fill gaps in understanding
5. **Quiz** — answer retrieval questions
6. **Track** — update your progress

Repeat daily. Synthesize weekly. Produce final outputs when complete.

---

## Repository Structure

```
edps-method/
├── README.md
├── books/
│   ├── _registry.yaml          # Roadmap across all books
│   └── wealth-of-nations/      # Example book
│       ├── meta.yaml           # Book metadata
│       ├── sections.yaml       # Section plan
│       ├── progress.yaml       # Your progress
│       ├── outputs/            # Final deliverables
│       ├── sections/           # Per-section materials
│       └── weekly/             # Weekly synthesis notes
├── templates/                  # Reusable templates
├── tools/                      # Build scripts
├── site/                       # Generated GitHub Pages
└── .github/workflows/          # CI/CD
```

---

## The Science

See [workflow-diagram.md](./docs/workflow-diagram.md) for full research citations and methodology.


**Key findings we implement:**

1. **Active recall beats passive review** — You write `recall.md` from memory before looking at sources
2. **Spaced repetition beats cramming** — Daily new sections + review of older sections
3. **Multimodal encoding improves retention** — Listen → Write → Read → Quiz
4. **Cognitive scaffolds reduce overload** — Claims map before reading
5. **Interleaving beats blocking** — Weekly quizzes mix questions across sections

---

## Progress

<!-- Auto-updated by build_index.py -->

| Book | Status | Progress |
|------|--------|----------|
| The Wealth of Nations | 🟡 In Progress | 0% |

---

## License

MIT

---

*Named in honor of Hermann Ebbinghaus, John Dunlosky, Allan Paivio, and John Sweller — whose research made this possible.*
