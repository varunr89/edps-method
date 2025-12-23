# Book-Level Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `edps generate` to create book-level outputs (templates + AI-generated) and update README with full workflow documentation.

**Architecture:** Add book-level generation phase after section-level generation. Templates are string constants; AI content uses new prompt files. New `--type` options: `book`, `sections`, `all` (default).

**Tech Stack:** Python, Typer CLI, YAML, existing LLM client

---

## Task 1: Create Book-Level Template Constants

**Files:**
- Modify: `tools/edps/commands/generate.py:19-59` (add after RECALL_TEMPLATE)

**Step 1: Add template constants**

Add these constants after `RECALL_TEMPLATE` in generate.py:

```python
# Template for one-pager.md - reader writes final distillation
ONE_PAGER_TEMPLATE = """<!-- TEMPLATE: Fill in sections below after completing all sections -->
# {book_title}: One-Pager

> Generator: 👤 Reader-written
> Author: {author}
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
"""

# Template for modern-mapping.md - reader writes contemporary connections
MODERN_MAPPING_TEMPLATE = """<!-- TEMPLATE: Fill in sections below after completing the one-pager -->
# Modern Mapping: {book_title}

> Generator: 👤 Reader-written
> Completed: [YYYY-MM-DD]

---

## Domain 1: [e.g., Technology & Labor]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 2: [e.g., Trade & Globalization]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 3: [e.g., Government & Regulation]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 4: [e.g., Inequality & Distribution]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 5: [e.g., Consumer Behavior]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

---

## Where the Book Falls Short

[What modern phenomena would surprise or confuse the author? What has changed since publication that invalidates parts of the argument?]
"""

# Template for weekly synthesis - reader copies to weekly/YYYY-MM-DD.md
WEEKLY_TEMPLATE = """<!-- TEMPLATE: Copy this file to weekly/YYYY-MM-DD.md when ready -->
# Weekly Synthesis

> Generator: 👤 Reader-written
> Week of: [YYYY-MM-DD]
> Sections covered: [001] - [00X]

---

## Top 3 Claims This Week

*What are the most important ideas from the sections you completed?*

1. **[Claim 1]**: [One sentence explanation]

2. **[Claim 2]**: [One sentence explanation]

3. **[Claim 3]**: [One sentence explanation]

---

## How They Connect

*3-5 sentences explaining how these claims relate to each other. Are they building blocks? Tensions? Different facets of one idea?*

[Your synthesis]

---

## One Strong Objection

*What's the best counterargument to what you learned this week? State it fairly — as if you believed it.*

[The objection in 2-3 sentences]

---

## My Response

*How would the author respond? How do YOU respond?*

[Your response in 2-3 sentences]

---

## Modern Connection

*One specific thing in today's world that this week's reading helps explain. Be concrete — name a company, policy, technology, or event.*

**Modern phenomenon**: [What you're connecting to]

**How this week's reading explains it**: [2-3 sentences]

---

## Gaps & Questions

*What are you still unsure about? What do you need to revisit?*

- [ ] [Question or concept to revisit]
- [ ] [Question or concept to revisit]
- [ ] [Optional third item]

---

## Interleaved Quiz Score

*If you took an interleaved quiz mixing questions from multiple sections:*

**Score**: [ ] / [ ]
**Sections with weakest recall**: [list section IDs]

---

## Time Log

| Activity | Time |
|----------|------|
| New sections completed | [X] |
| Total learning time | [X] hours |
| Synthesis writing | [X] minutes |

---

## Next Week

*What sections will you tackle? Any adjustments to your approach?*

[Your plan]
"""
```

**Step 2: Commit**

```bash
git add tools/edps/commands/generate.py
git commit -m "feat: add book-level template constants for one-pager, modern-mapping, weekly"
```

---

## Task 2: Create Teachable Outline Prompt

**Files:**
- Create: `tools/edps/prompts/teachable-outline.txt`

**Step 1: Create prompt file**

```
You are creating a 60-minute teaching outline for "{book_title}" by {author}.

## Book Details
- Title: {book_title}
- Author: {author}
- Total sections: {section_count}

## All Section Summaries
{all_summaries}

## Task
Create a comprehensive 60-minute teaching plan following this EXACT format:

---

# Teaching {book_title} in 60 Minutes

> Generator: 🤖→👤 AI-drafted, reader-refined
> Generated: {date}

## Audience

[Describe the ideal audience: educated general reader, undergraduate, professional. What prior knowledge is assumed?]

## Learning Objectives

By the end, students will be able to:
1. [First testable objective - what can they explain?]
2. [Second testable objective - what can they analyze?]
3. [Third testable objective - what can they apply?]

## Outline

### Segment 1: [Title] (10 min)
- **Key point**: [One sentence capturing the core idea]
- **From the book**: [Specific example or argument from the text]
- **Modern parallel**: [Contemporary example that illustrates this]
- **Transition**: [How this leads to the next segment]

### Segment 2: [Title] (10 min)
- **Key point**: [One sentence capturing the core idea]
- **From the book**: [Specific example or argument from the text]
- **Modern parallel**: [Contemporary example that illustrates this]
- **Transition**: [How this leads to the next segment]

### Segment 3: [Title] (10 min)
- **Key point**: [One sentence capturing the core idea]
- **From the book**: [Specific example or argument from the text]
- **Modern parallel**: [Contemporary example that illustrates this]
- **Transition**: [How this leads to the next segment]

### Segment 4: [Title] (10 min)
- **Key point**: [One sentence capturing the core idea]
- **From the book**: [Specific example or argument from the text]
- **Modern parallel**: [Contemporary example that illustrates this]
- **Transition**: [How this leads to the next segment]

### Segment 5: [Title] (10 min)
- **Key point**: [One sentence capturing the core idea]
- **From the book**: [Specific example or argument from the text]
- **Modern parallel**: [Contemporary example that illustrates this]
- **Transition**: [How this leads to the next segment]

### Segment 6: Synthesis & Discussion (10 min)
- **Recap**: [The 5 key points in one paragraph]
- **Discussion questions**:
  1. [Open-ended question for group discussion]
  2. [Question that challenges assumptions]
  3. [Question connecting to students' experiences]
- **If you remember one thing**: [The single most important takeaway]

## Predicted Student Questions

1. **Q**: [Likely question a student would ask]
   **A**: [Concise answer grounded in the text]

2. **Q**: [Likely question a student would ask]
   **A**: [Concise answer grounded in the text]

3. **Q**: [Likely question a student would ask]
   **A**: [Concise answer grounded in the text]

4. **Q**: [Likely question a student would ask]
   **A**: [Concise answer grounded in the text]

5. **Q**: [Likely question a student would ask]
   **A**: [Concise answer grounded in the text]

---

## Generation Notes

- Model: {model}
- Prompt version: 1.0
- Human edits: none
```

**Step 2: Commit**

```bash
git add tools/edps/prompts/teachable-outline.txt
git commit -m "feat: add teachable-outline prompt for book-level generation"
```

---

## Task 3: Create Question Bank Prompt

**Files:**
- Create: `tools/edps/prompts/question-bank.txt`

**Step 1: Create prompt file**

```
You are curating a comprehensive question bank for "{book_title}" by {author}.

## Book Details
- Title: {book_title}
- Author: {author}
- Sections covered: {section_range}

## All Section Quizzes
{all_quizzes}

## Task
Create a comprehensive question bank by:
1. Selecting the 25 best short-answer questions from the section quizzes (ensuring coverage across all major sections)
2. Creating 5 new essay prompts that require synthesis across sections

Follow this EXACT format:

---

# Question Bank: {book_title}

> Generator: 🤖 AI-curated
> Generated: {date}
> Sections covered: {section_range}

---

## Short Answer (25 questions)

*Answer each in 2-3 sentences.*

1. [Question text] *(Section {id})*
2. [Question text] *(Section {id})*
3. [Question text] *(Section {id})*
4. [Question text] *(Section {id})*
5. [Question text] *(Section {id})*
6. [Question text] *(Section {id})*
7. [Question text] *(Section {id})*
8. [Question text] *(Section {id})*
9. [Question text] *(Section {id})*
10. [Question text] *(Section {id})*
11. [Question text] *(Section {id})*
12. [Question text] *(Section {id})*
13. [Question text] *(Section {id})*
14. [Question text] *(Section {id})*
15. [Question text] *(Section {id})*
16. [Question text] *(Section {id})*
17. [Question text] *(Section {id})*
18. [Question text] *(Section {id})*
19. [Question text] *(Section {id})*
20. [Question text] *(Section {id})*
21. [Question text] *(Section {id})*
22. [Question text] *(Section {id})*
23. [Question text] *(Section {id})*
24. [Question text] *(Section {id})*
25. [Question text] *(Section {id})*

---

## Essay Prompts (5 questions)

*Answer each in 500-800 words.*

### 1. Synthesis
[Prompt requiring the reader to connect ideas across multiple chapters. Should ask them to trace an argument or theme through the entire book.]

### 2. Comparison
[Prompt asking the reader to compare the author's ideas with another thinker, framework, or school of thought. Name a specific comparison point.]

### 3. Application
[Prompt asking the reader to apply the book's ideas to a specific modern issue, policy debate, or contemporary phenomenon. Be specific about the context.]

### 4. Critique
[Prompt asking the reader to critically evaluate the author's argument. What are the weaknesses? What evidence is missing? What assumptions are questionable?]

### 5. Reflection
[Prompt asking: "How has reading this book changed your thinking about [specific topic]?" Should invite personal reflection grounded in the text.]

---

## Generation Notes

- Model: {model}
- Prompt version: 1.0
- Human edits: none
```

**Step 2: Commit**

```bash
git add tools/edps/prompts/question-bank.txt
git commit -m "feat: add question-bank prompt for book-level generation"
```

---

## Task 4: Write Failing Test for Book-Level Template Generation

**Files:**
- Modify: `tests/test_cmd_generate.py`

**Step 1: Add test for book-level templates**

Add at end of file:

```python
def test_generate_book_creates_outputs_directory():
    """edps generate --type book creates outputs/ and weekly/ directories with templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup book structure with multiple sections
        book_dir = tmpdir / "books" / "test-book"
        for section_id in ["001", "002"]:
            section_dir = book_dir / "sections" / section_id
            section_dir.mkdir(parents=True)
            (section_dir / f"EDPS-test-book-{section_id}.txt").write_text(f"Content for section {section_id}.")
            (section_dir / "summary.md").write_text(f"# Summary {section_id}\n\nTLDR content.")
            (section_dir / "quiz.md").write_text(f"# Quiz {section_id}\n\n1. Question?")

        # Create sections.yaml
        (book_dir / "sections.yaml").write_text(yaml.dump({
            "sections": [
                {"id": "001", "title": "Chapter 1", "location": "Ch 1", "word_count": 500},
                {"id": "002", "title": "Chapter 2", "location": "Ch 2", "word_count": 500},
            ]
        }))

        # Create meta.yaml
        (book_dir / "meta.yaml").write_text(yaml.dump({
            "title": "Test Book",
            "author": "Test Author",
        }))

        # Create config
        config_dir = tmpdir / ".edps"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(yaml.dump({
            "azure": {
                "endpoint": "https://test.azure.com",
                "api_key": "test-key",
            }
        }))

        # Mock LLM for AI-generated content
        mock_response = LLMResponse(
            content="# Teaching Test Book\n\nGenerated content.",
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
            model="claude-sonnet-4-20250514",
        )

        with patch("edps.commands.generate.LLMClient") as MockClient:
            mock_client = MagicMock()
            mock_client.preview.return_value = MagicMock(
                input_tokens=100,
                estimated_output_tokens=500,
                estimated_cost=0.01,
                model="claude-sonnet-4-20250514",
                prompt="test prompt",
            )
            mock_client.complete.return_value = mock_response
            mock_client.default_model = "claude-sonnet-4-20250514"
            MockClient.return_value = mock_client

            result = runner.invoke(app, [
                "generate", "test-book",
                "--books-dir", str(tmpdir / "books"),
                "--config-path", str(config_dir / "config.yaml"),
                "--yes",
                "--type", "book",
            ])

        assert result.exit_code == 0, result.output

        # Check outputs/ directory created
        outputs_dir = book_dir / "outputs"
        assert outputs_dir.exists()

        # Check template files created
        assert (outputs_dir / "one-pager.md").exists()
        assert "TEMPLATE" in (outputs_dir / "one-pager.md").read_text()
        assert "Test Book" in (outputs_dir / "one-pager.md").read_text()

        assert (outputs_dir / "modern-mapping.md").exists()
        assert "TEMPLATE" in (outputs_dir / "modern-mapping.md").read_text()

        # Check AI-generated files created
        assert (outputs_dir / "teachable-outline.md").exists()
        assert (outputs_dir / "question-bank.md").exists()

        # Check weekly/ directory created with template
        weekly_dir = book_dir / "weekly"
        assert weekly_dir.exists()
        assert (weekly_dir / "_template.md").exists()
        assert "Weekly Synthesis" in (weekly_dir / "_template.md").read_text()
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH="$PWD/tools" python -m pytest tests/test_cmd_generate.py::test_generate_book_creates_outputs_directory -v
```

Expected: FAIL - `--type book` not recognized

**Step 3: Commit failing test**

```bash
git add tests/test_cmd_generate.py
git commit -m "test: add failing test for book-level generation"
```

---

## Task 5: Implement Book-Level Generation in generate.py

**Files:**
- Modify: `tools/edps/commands/generate.py`

**Step 1: Update gen_type option and add book generation logic**

Replace the `generate` function and add helper functions. The key changes:

1. Update `--type` option to accept: `all`, `sections`, `book`, `summary`, `podcast`, `quiz`, `recall`
2. Add `_generate_book_content()` function
3. Call book generation after section generation when appropriate

```python
"""Generate command - create AI content and templates for sections."""
from datetime import date
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

from edps.config import load_config
from edps.core.llm import LLMClient
from edps.core.prompts import load_prompt, render_prompt
from edps.core.ui import confirm_action

console = Console()


# Template for recall.md - human-writable memory exercise
RECALL_TEMPLATE = """<!-- TEMPLATE: Fill in sections below -->
# Recall: Section {section_id}

> Section: {title}
> Date: {date}
> Time spent: [X minutes]

---

## From Memory (before re-reading)

*Write these BEFORE looking at source or summary:*

1. [Main claim as I remember it]
2. [Key mechanism or process]
3. [Example I remember]
4. [Modern parallel that came to mind]
5. [Something I'm unsure about]

---

## After Selective Reading

*Corrections after reviewing source:*

- Correction 1: [what I got wrong or missed]
- Correction 2: [additional nuance]

---

## Self-Score

- Recall accuracy: [0-5]
- Confidence: [low / medium / high]

---

## One Sentence I'd Tell Someone

[If I had 30 seconds to explain this section, I'd say...]
"""


# Template for one-pager.md - reader writes final distillation
ONE_PAGER_TEMPLATE = """<!-- TEMPLATE: Fill in sections below after completing all sections -->
# {book_title}: One-Pager

> Generator: 👤 Reader-written
> Author: {author}
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
"""

# Template for modern-mapping.md - reader writes contemporary connections
MODERN_MAPPING_TEMPLATE = """<!-- TEMPLATE: Fill in sections below after completing the one-pager -->
# Modern Mapping: {book_title}

> Generator: 👤 Reader-written
> Completed: [YYYY-MM-DD]

---

## Domain 1: [e.g., Technology & Labor]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 2: [e.g., Trade & Globalization]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 3: [e.g., Government & Regulation]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 4: [e.g., Inequality & Distribution]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

## Domain 5: [e.g., Consumer Behavior]

- **Book concept**: [What the author said]
- **Modern manifestation**: [How it shows up today]
- **Specific example**: [Company, policy, or event]
- **What the author would say**: [Grounded speculation]

---

## Where the Book Falls Short

[What modern phenomena would surprise or confuse the author? What has changed since publication that invalidates parts of the argument?]
"""

# Template for weekly synthesis - reader copies to weekly/YYYY-MM-DD.md
WEEKLY_TEMPLATE = """<!-- TEMPLATE: Copy this file to weekly/YYYY-MM-DD.md when ready -->
# Weekly Synthesis

> Generator: 👤 Reader-written
> Week of: [YYYY-MM-DD]
> Sections covered: [001] - [00X]

---

## Top 3 Claims This Week

*What are the most important ideas from the sections you completed?*

1. **[Claim 1]**: [One sentence explanation]

2. **[Claim 2]**: [One sentence explanation]

3. **[Claim 3]**: [One sentence explanation]

---

## How They Connect

*3-5 sentences explaining how these claims relate to each other. Are they building blocks? Tensions? Different facets of one idea?*

[Your synthesis]

---

## One Strong Objection

*What's the best counterargument to what you learned this week? State it fairly — as if you believed it.*

[The objection in 2-3 sentences]

---

## My Response

*How would the author respond? How do YOU respond?*

[Your response in 2-3 sentences]

---

## Modern Connection

*One specific thing in today's world that this week's reading helps explain. Be concrete — name a company, policy, technology, or event.*

**Modern phenomenon**: [What you're connecting to]

**How this week's reading explains it**: [2-3 sentences]

---

## Gaps & Questions

*What are you still unsure about? What do you need to revisit?*

- [ ] [Question or concept to revisit]
- [ ] [Question or concept to revisit]
- [ ] [Optional third item]

---

## Interleaved Quiz Score

*If you took an interleaved quiz mixing questions from multiple sections:*

**Score**: [ ] / [ ]
**Sections with weakest recall**: [list section IDs]

---

## Time Log

| Activity | Time |
|----------|------|
| New sections completed | [X] |
| Total learning time | [X] hours |
| Synthesis writing | [X] minutes |

---

## Next Week

*What sections will you tackle? Any adjustments to your approach?*

[Your plan]
"""


def generate(
    book_slug: str = typer.Argument(..., help="Book slug"),
    section_id: Optional[str] = typer.Argument(None, help="Section ID (e.g., '001'). If omitted, generates all."),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir", help="Path to books directory"),
    config_path: Optional[Path] = typer.Option(None, "--config-path", help="Path to config file"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
    gen_type: str = typer.Option("all", "--type", "-t", help="Type: all, sections, book, summary, podcast, quiz, recall"),
) -> None:
    """Generate AI content for book sections and book-level outputs."""

    # Load config
    config = load_config(config_path)

    # Setup paths
    if books_dir is None:
        books_dir = Path.cwd() / "books"

    book_dir = books_dir / book_slug
    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Book not found: {book_dir}")
        raise typer.Exit(1)

    # Load book metadata
    meta_path = book_dir / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
    else:
        meta = {"title": book_slug, "author": "Unknown"}

    # Load sections
    sections_path = book_dir / "sections.yaml"
    if not sections_path.exists():
        console.print("[red]Error:[/red] sections.yaml not found. Run 'edps ingest' first.")
        raise typer.Exit(1)

    sections_data = yaml.safe_load(sections_path.read_text())
    sections = sections_data.get("sections", [])

    # Create LLM client
    client = LLMClient(config)

    # Determine what to generate
    generate_sections = gen_type in ["all", "sections", "summary", "podcast", "quiz", "recall"]
    generate_book = gen_type in ["all", "book"]

    # Section-level generation
    if generate_sections:
        # Filter to specific section if requested
        target_sections = sections
        if section_id:
            target_sections = [s for s in sections if s["id"] == section_id]
            if not target_sections:
                console.print(f"[red]Error:[/red] Section not found: {section_id}")
                raise typer.Exit(1)

        # Determine section types to generate
        if gen_type in ["summary", "podcast", "quiz", "recall"]:
            section_types = [gen_type]
        else:
            section_types = ["summary", "podcast", "quiz", "recall"]

        # Generate for each section
        for section in target_sections:
            section_dir = book_dir / "sections" / section["id"]

            # Look for source file
            source_filename = f"EDPS-{book_slug}-{section['id']}.txt"
            source_path = section_dir / source_filename
            if not source_path.exists():
                source_path = section_dir / "source.txt"

            if not source_path.exists():
                console.print(f"[yellow]Warning:[/yellow] No source file for section {section['id']}, skipping")
                continue

            source_text = source_path.read_text(encoding="utf-8")

            for type_item in section_types:
                output_path = section_dir / f"{type_item}.md"

                if output_path.exists():
                    console.print(f"[dim]Skipping {section['id']}/{type_item}.md (exists)[/dim]")
                    continue

                result = _generate_section_content(
                    client=client,
                    gen_type=type_item,
                    section=section,
                    source_text=source_text,
                    meta=meta,
                    section_dir=section_dir,
                    skip_confirm=yes,
                    book_slug=book_slug,
                )

                if result == "quit":
                    raise typer.Exit(0)
                elif result == "skip":
                    continue

                console.print(f"[green]✓[/green] Created {output_path}")

    # Book-level generation
    if generate_book:
        _generate_book_content(
            client=client,
            book_dir=book_dir,
            meta=meta,
            sections=sections,
            skip_confirm=yes,
            book_slug=book_slug,
        )


def _generate_section_content(
    client: LLMClient,
    gen_type: str,
    section: dict,
    source_text: str,
    meta: dict,
    section_dir: Path,
    skip_confirm: bool,
    book_slug: str = "",
) -> str:
    """Generate a single piece of section content.

    Returns: "done", "skip", or "quit"
    """
    # Podcast is a pass-through for now
    if gen_type == "podcast":
        output_path = section_dir / "podcast.md"
        source_filename = f"EDPS-{book_slug}-{section['id']}.txt" if book_slug else "source.txt"
        placeholder = f"""# Podcast: Section {section['id']}

> **Use NotebookLM**: Upload the source text (`{source_filename}`) to [NotebookLM](https://notebooklm.google.com/) to generate an audio overview.

This placeholder exists to preserve the workflow structure for future podcast generation features.
"""
        output_path.write_text(placeholder, encoding="utf-8")
        console.print(f"[dim]Skipping podcast LLM call (use NotebookLM instead)[/dim]")
        return "done"

    # Recall is a human-writable template
    if gen_type == "recall":
        output_path = section_dir / "recall.md"
        content = RECALL_TEMPLATE.format(
            section_id=section["id"],
            title=section.get("title", ""),
            date=date.today().isoformat(),
        )
        output_path.write_text(content, encoding="utf-8")
        console.print(f"[dim]Created recall.md template (human-writable)[/dim]")
        return "done"

    # Load and render prompt
    template = load_prompt(gen_type)

    # For quiz, we need the summary
    summary_text = ""
    if gen_type == "quiz":
        summary_path = section_dir / "summary.md"
        if summary_path.exists():
            summary_text = summary_path.read_text()

    prompt = render_prompt(
        template,
        book_title=meta.get("title", "Unknown"),
        author=meta.get("author", "Unknown"),
        section_id=section["id"],
        section_title=section.get("title", ""),
        location=section.get("location", ""),
        source_text=source_text,
        summary_text=summary_text,
        date=date.today().isoformat(),
        model=client.default_model,
    )

    # Preview
    preview = client.preview(prompt, estimated_output_tokens=1500)

    # Confirm
    if not skip_confirm:
        action = confirm_action(
            title=f"Generate {gen_type}.md",
            section=f"{section['id']}: {section.get('title', '')[:40]}",
            preview=preview,
        )

        if action == "quit":
            return "quit"
        elif action == "skip":
            return "skip"
        elif action == "view":
            console.print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
            return _generate_section_content(client, gen_type, section, source_text, meta, section_dir, skip_confirm)

    # Execute
    response = client.complete(prompt)

    # Save
    output_path = section_dir / f"{gen_type}.md"
    output_path.write_text(response.content, encoding="utf-8")

    console.print(f"[dim]Tokens: {response.input_tokens} in, {response.output_tokens} out. Cost: ${response.cost:.4f}[/dim]")

    return "done"


def _generate_book_content(
    client: LLMClient,
    book_dir: Path,
    meta: dict,
    sections: list,
    skip_confirm: bool,
    book_slug: str = "",
) -> None:
    """Generate book-level outputs (templates and AI-generated)."""
    console.print("\n[bold]Generating book-level outputs...[/bold]")

    # Create directories
    outputs_dir = book_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    weekly_dir = book_dir / "weekly"
    weekly_dir.mkdir(exist_ok=True)

    book_title = meta.get("title", book_slug)
    author = meta.get("author", "Unknown")

    # Generate templates (no LLM call)
    _write_template(outputs_dir / "one-pager.md", ONE_PAGER_TEMPLATE, book_title=book_title, author=author)
    _write_template(outputs_dir / "modern-mapping.md", MODERN_MAPPING_TEMPLATE, book_title=book_title)
    _write_template(weekly_dir / "_template.md", WEEKLY_TEMPLATE)

    # Collect all summaries and quizzes for AI-generated content
    all_summaries = []
    all_quizzes = []

    for section in sections:
        section_dir = book_dir / "sections" / section["id"]

        summary_path = section_dir / "summary.md"
        if summary_path.exists():
            all_summaries.append(f"## Section {section['id']}: {section.get('title', '')}\n\n{summary_path.read_text()}")

        quiz_path = section_dir / "quiz.md"
        if quiz_path.exists():
            all_quizzes.append(f"## Section {section['id']}: {section.get('title', '')}\n\n{quiz_path.read_text()}")

    section_ids = [s["id"] for s in sections]
    section_range = f"{section_ids[0]}-{section_ids[-1]}" if section_ids else "none"

    # Generate teachable-outline.md (AI-generated)
    teachable_path = outputs_dir / "teachable-outline.md"
    if not teachable_path.exists() and all_summaries:
        _generate_ai_book_content(
            client=client,
            output_path=teachable_path,
            prompt_name="teachable-outline",
            meta=meta,
            all_content="\n\n---\n\n".join(all_summaries),
            content_key="all_summaries",
            section_count=len(sections),
            section_range=section_range,
            skip_confirm=skip_confirm,
        )
    elif teachable_path.exists():
        console.print(f"[dim]Skipping outputs/teachable-outline.md (exists)[/dim]")

    # Generate question-bank.md (AI-generated)
    qbank_path = outputs_dir / "question-bank.md"
    if not qbank_path.exists() and all_quizzes:
        _generate_ai_book_content(
            client=client,
            output_path=qbank_path,
            prompt_name="question-bank",
            meta=meta,
            all_content="\n\n---\n\n".join(all_quizzes),
            content_key="all_quizzes",
            section_count=len(sections),
            section_range=section_range,
            skip_confirm=skip_confirm,
        )
    elif qbank_path.exists():
        console.print(f"[dim]Skipping outputs/question-bank.md (exists)[/dim]")


def _write_template(path: Path, template: str, **kwargs) -> None:
    """Write a template file if it doesn't exist."""
    if path.exists():
        console.print(f"[dim]Skipping {path.name} (exists)[/dim]")
        return

    content = template.format(**kwargs) if kwargs else template
    path.write_text(content, encoding="utf-8")
    console.print(f"[green]✓[/green] Created {path.parent.name}/{path.name}")


def _generate_ai_book_content(
    client: LLMClient,
    output_path: Path,
    prompt_name: str,
    meta: dict,
    all_content: str,
    content_key: str,
    section_count: int,
    section_range: str,
    skip_confirm: bool,
) -> None:
    """Generate AI book-level content."""
    template = load_prompt(prompt_name)

    prompt_vars = {
        "book_title": meta.get("title", "Unknown"),
        "author": meta.get("author", "Unknown"),
        content_key: all_content,
        "section_count": section_count,
        "section_range": section_range,
        "date": date.today().isoformat(),
        "model": client.default_model,
    }

    prompt = render_prompt(template, **prompt_vars)

    # Preview
    preview = client.preview(prompt, estimated_output_tokens=2000)

    # Confirm
    if not skip_confirm:
        action = confirm_action(
            title=f"Generate {output_path.name}",
            section="book-level",
            preview=preview,
        )

        if action in ["quit", "skip"]:
            return
        elif action == "view":
            console.print(prompt[:3000] + "..." if len(prompt) > 3000 else prompt)
            return _generate_ai_book_content(
                client, output_path, prompt_name, meta, all_content,
                content_key, section_count, section_range, skip_confirm
            )

    # Execute
    response = client.complete(prompt)
    output_path.write_text(response.content, encoding="utf-8")

    console.print(f"[green]✓[/green] Created {output_path.parent.name}/{output_path.name}")
    console.print(f"[dim]Tokens: {response.input_tokens} in, {response.output_tokens} out. Cost: ${response.cost:.4f}[/dim]")
```

**Step 2: Run test to verify it passes**

```bash
PYTHONPATH="$PWD/tools" python -m pytest tests/test_cmd_generate.py::test_generate_book_creates_outputs_directory -v
```

Expected: PASS

**Step 3: Run all generate tests**

```bash
PYTHONPATH="$PWD/tools" python -m pytest tests/test_cmd_generate.py -v
```

Expected: All PASS

**Step 4: Commit**

```bash
git add tools/edps/commands/generate.py
git commit -m "feat: implement book-level generation for outputs/ and weekly/ directories"
```

---

## Task 6: Update README with Full Workflow Documentation

**Files:**
- Modify: `README.md`

**Step 1: Add Weekly Synthesis section after "The Daily Workflow"**

Find the "## How the Dashboard Updates" section and insert before it:

```markdown
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
```

**Step 2: Update Repository Structure section**

Replace the existing structure diagram with:

```markdown
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
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add weekly synthesis, book completion, and spaced review to README"
```

---

## Task 7: Test End-to-End with Existing Book

**Files:**
- Test against: `books/wealth-of-nations/`

**Step 1: Run book-level generation**

```bash
cd /Users/varunr/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/Varun/Reading/edps-method
source .venv/bin/activate
PYTHONPATH="$PWD/tools" python -m edps.cli generate wealth-of-nations --type book --yes
```

**Step 2: Verify outputs created**

```bash
ls -la books/wealth-of-nations/outputs/
ls -la books/wealth-of-nations/weekly/
```

Expected:
- `outputs/one-pager.md` - template with "Wealth of Nations" in title
- `outputs/modern-mapping.md` - template
- `outputs/teachable-outline.md` - AI-generated (if summaries exist)
- `outputs/question-bank.md` - AI-generated (if quizzes exist)
- `weekly/_template.md` - weekly synthesis template

**Step 3: Commit generated files**

```bash
git add books/wealth-of-nations/outputs/ books/wealth-of-nations/weekly/
git commit -m "feat: generate book-level outputs for wealth-of-nations"
```

---

## Task 8: Run Full Test Suite

**Step 1: Run all tests**

```bash
PYTHONPATH="$PWD/tools" python -m pytest tests/ -v
```

Expected: All PASS

**Step 2: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address test failures from book-level generation"
```

---

## Summary

| Task | Files | Type |
|------|-------|------|
| 1 | `generate.py` | Add template constants |
| 2 | `prompts/teachable-outline.txt` | Create prompt |
| 3 | `prompts/question-bank.txt` | Create prompt |
| 4 | `tests/test_cmd_generate.py` | Add failing test |
| 5 | `generate.py` | Implement book generation |
| 6 | `README.md` | Document full workflow |
| 7 | Manual | End-to-end test |
| 8 | All | Run test suite |
