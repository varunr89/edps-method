# Site Redesign: Warm & Scholarly Single-Page

**Date:** 2025-12-21
**Status:** Approved

## Goals

1. Improve readability (current site is overwhelming with all books listed immediately)
2. Add personal touch and public accountability message
3. Prominent links to GitHub repo and methodology doc
4. Warm, scholarly aesthetic

## Design Decisions

### Approach
Single HTML page with collapsible accordion sections. No multi-page navigation.

### Tone
Personal and conversational. Varun introduces himself and explains the public accountability angle.

### Visual Style
Warm & scholarly:
- Cream/sepia background (#f5f1e8)
- Dark brown text (#3d3328)
- Muted gold accents (#8b7355)
- Serif headings (Georgia), sans-serif body

## Page Structure

### 1. Hero Section
- Large title: "THE EDPS METHOD"
- Subtitle: "Ebbinghaus · Dunlosky · Paivio · Sweller"
- "What is this?" link → methodology doc
- Personal intro paragraph about accountability
- Three stat cards: total books, active, completed
- Prominent GitHub repo link

### 2. Currently Reading
- Callout section showing any in-progress books
- Direct link to continue reading

### 3. Reading Roadmap (Accordions)
- 10 category headers, each collapsible
- Shows book count and category progress when collapsed
- Expands to show book list with status indicators:
  - ○ not started
  - ◐ in progress
  - ● complete
- Book titles link to detail pages

### 4. Footer
- Last updated timestamp
- Secondary links

## Technical Implementation

- Pure HTML/CSS (no JavaScript required)
- CSS accordions using `<details>`/`<summary>` elements
- `build_index.py` generates the HTML from YAML registry
- Embedded CSS in `<style>` block (no external dependencies)
- Same workflow: edit YAML → push → site auto-rebuilds
