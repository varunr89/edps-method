# AI Evaluation & Quiz Redesign

**Date:** 2025-12-27
**Status:** Design approved, pending implementation

---

## Problem Statement

### Current AI Evaluation
- ~150 words, ~30-second read
- Table format: Question | Status | Score | Feedback (one line each)
- Tells you *what* was wrong, not *how* to improve
- No writing feedback, no reasoning analysis
- Not a learning experience—just scoring

### Current Quiz
- Fixed 8-question structure every section
- Same types: Main Claim → Mechanism → Example → Define x2 → Teach It Back → Counterfactual → Modern Connection
- All prose answers, no variety
- Gets repetitive after a few sections

---

## Design Goals

1. **Evaluation as learning** — 3-minute read that teaches, not 30-second score report
2. **Holistic feedback** — Source mastery + reasoning quality + writing craft
3. **Quiz variety** — Different question types prevent autopilot
4. **Adaptive format** — AI adjusts MCQ/prose mix based on section content
5. **Harder MCQs** — Multi-answer, none-correct, assumption-testing

---

## AI Evaluation Design

### Structure

```markdown
## AI Feedback

**Evaluated:** {date} | **Source:** {source_file}
**Scores:** Recall {X}/5 | Quiz {Y}/{total}

---

### Per-Answer Analysis

#### Q1: {Title} ({score})
**Accuracy:** {Did they get the facts right? What's missing or wrong?}
**Reasoning:** {Is the logic sound? Cause-effect correct? Assumptions valid?}
**Writing:** {Precision, clarity, economy. Specific suggestions.}

#### Q2: {Title} ({score})
[...same structure...]

[...continues for all questions...]

---

### Thematic Insights

#### Source Mastery
{Patterns across answers—what they consistently get, what they miss.
Specific examples from their answers. "You wrote X, but Smith says Y."}

#### Reasoning Quality
{How they build arguments. Logical gaps. Depth of analysis.
Strengths to build on. Edges to develop.}

#### Writing Craft
**Precision:** {X}/5 — {Key terms drifting? Hedges flattened?}
**Clarity:** {X}/5 — {Main points buried? Structure issues?}
**Economy:** {X}/5 — {Word count vs. meaning ratio. Specific cuts.}

{One concrete fix to practice.}

---

### Tutor's Note

{Narrative synthesis. 3-4 paragraphs.}

{What they're doing well—specific praise with evidence.}

{2-3 things to carry forward, explained with depth:}
1. {First insight—why it matters, how to apply it}
2. {Second insight—connect to their specific mistakes}
3. {Third insight—deeper implication they missed}

{Prompt for next section—what to watch for.}
```

### Target Length
- Per-Answer Analysis: ~50 words × 8-12 questions = ~400-600 words
- Thematic Insights: ~250 words
- Tutor's Note: ~150 words
- **Total: ~800-1000 words (~3-4 minute read)**

### Evaluation Prompt Changes

Update `build_evaluation_prompt()` in `evaluation.py` to request:

1. Per-answer analysis with Accuracy/Reasoning/Writing breakdown
2. Thematic patterns across all answers
3. Writing craft scores (precision, clarity, economy each 1-5)
4. Narrative tutor's note with specific forward-looking advice
5. No model answers—focus on improving *their* answer

---

## Quiz Design

### Structure

```markdown
# Quiz: Section {id}

> Generator: 🤖 AI-generated
> Format: {X} MCQ + {Y} prose (tailored to section content)
> Time estimate: 15-20 minutes

---

## Part A: Quick Recall (Multiple Choice)

*Some questions have one answer, some have multiple, some have none.
You must decide which case applies.*

### 1. {Hard conceptual question}
{Question requiring deep understanding to evaluate options}

- A) {Plausible option—may be distractor or correct}
- B) {Common misconception}
- C) {Related but different concept}
- D) {Subtle variation}

**Select:** ◯ One ◯ Multiple ◯ None    **Answer(s):** ___

[...continues for 3-8 MCQs based on section...]

---

## Part B: Deep Thinking (Prose)

*Question types vary by section. Focus on reasoning, not just recall.*

### {N}. Adversarial
{Strongest objection + how author might respond}

**Answer:** (3-5 sentences)

---

### {N+1}. Comparative
{Connect to previous section's concepts—dependencies, tensions}

**Answer:** (3-5 sentences)

---

### {N+2}. Socratic
{Examine an assumption—does it matter? What if it's wrong?}

**Answer:** (4-6 sentences)

---

### {N+3}. Synthesis
{Bridge to modern concept or thinker}

**Answer:** (4-6 sentences)

---

## Score

- MCQ: __ / {X}
- Prose: __ / {Y}
- **Total: __ / {X+Y}**
```

### MCQ Design Principles

1. **Questions must be hard** — Options visible, so difficulty comes from question complexity
2. **Test understanding, not recall** — "What assumption does this depend on?" not "What did Smith say?"
3. **Variable answer count:**
   - Some have one correct answer
   - Some have multiple correct answers
   - Some have no correct answer (all are wrong or incomplete)
4. **Distractor types (mixed):**
   - Common misconceptions
   - Plausible but wrong (misses key nuance)
   - Related but different (concepts that could be confused)

### MCQ Question Types

- **Assumption questions:** "This argument depends on which unstated assumption(s)?"
- **Counter-evidence questions:** "Which would count as evidence AGAINST this thesis?"
- **Precise meaning questions:** "This quote supports which claim(s)?" (parse carefully)
- **Scope questions:** "This argument applies to which cases?" (not over-generalize)
- **Relationship questions:** "How does concept X relate to concept Y?"

### Prose Question Types

| Type | Purpose | Prompt Pattern |
|------|---------|----------------|
| **Adversarial** | Steel-man opposition, then defend | "Strongest objection to X? How might author respond?" |
| **Comparative** | Build cross-section connections | "How does this connect to [previous concept]? Dependencies?" |
| **Socratic** | Examine assumptions, test robustness | "Author assumes X. Does it matter? What if wrong?" |
| **Synthesis** | Bridge historical to modern | "How does this anticipate/fail to anticipate [modern concept]?" |

### Distribution Logic

AI analyzes section content and adjusts:

| Section Type | MCQs | Prose | Emphasis |
|--------------|------|-------|----------|
| **Terminology-heavy** | 6-8 | 3-4 | MCQs test precise definitions; Prose: Comparative, Synthesis |
| **Argument-heavy** | 3-4 | 5-6 | MCQs test assumptions; Prose: Adversarial, Socratic |
| **Example-heavy** | 4-5 | 4-5 | MCQs test what examples prove; Prose: Synthesis, Comparative |

Cross-section rule: Every 3 consecutive sections must include at least one of each prose type.

---

## Implementation Plan

### Phase 1: Evaluation Redesign
1. Update `build_evaluation_prompt()` with new output format
2. Update `parse_evaluation_response()` to handle expanded JSON
3. Update `format_quiz_feedback()` and `format_recall_feedback()` for new markdown structure
4. Test on existing section 002

### Phase 2: Quiz Redesign
1. Rewrite `prompts/quiz.txt` with new format and instructions
2. Add MCQ parsing to evaluation (handle multi-answer, none-correct)
3. Update quiz generation command
4. Test on new section

### Phase 3: Polish
1. Tune prompt for consistent output quality
2. Adjust token limits (longer outputs need more tokens)
3. Update README with new quiz/evaluation format

---

## Files to Modify

| File | Changes |
|------|---------|
| `tools/edps/evaluation.py` | New prompt format, new parsing, new markdown output |
| `tools/edps/prompts/quiz.txt` | Complete rewrite with MCQ + variable prose |
| `tools/edps/config.py` | Increase `max_tokens` default (longer outputs) |
| `templates/quiz.md` | Update template structure |
| `README.md` | Document new format |

---

## Success Criteria

- [ ] Evaluation output is 800-1000 words (vs. current 150)
- [ ] Each answer gets Accuracy/Reasoning/Writing feedback
- [ ] Thematic insights identify patterns across answers
- [ ] Tutor's note provides actionable forward-looking advice
- [ ] Quiz includes 3-8 hard MCQs with multi/none-answer options
- [ ] Prose questions vary by type (Adversarial, Comparative, Socratic, Synthesis)
- [ ] Question distribution adapts to section content
- [ ] No two consecutive quizzes feel identical
