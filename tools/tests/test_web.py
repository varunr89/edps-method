"""Tests for EDPS web UI."""
import os
import pytest
from fastapi.testclient import TestClient

# Set books dir before importing app
os.environ["EDPS_BOOKS_DIR"] = os.path.join(os.path.dirname(__file__), "..", "..", "books")

from edps.web.app import app
from edps.web.parsers import parse_summary, parse_recall, parse_quiz, render_answer_with_highlights


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        """Health check returns OK status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestIndexPage:
    def test_index_page_loads(self, client):
        """Index page renders without error."""
        response = client.get("/")
        assert response.status_code == 200
        assert "EDPS" in response.text

    def test_index_contains_dashboard_title(self, client):
        """Index page contains dashboard title."""
        response = client.get("/")
        assert "EDPS Reading Dashboard" in response.text


class TestParsers:
    def test_parse_summary_extracts_tldr(self):
        """parse_summary extracts TLDR section."""
        content = """# Summary

## TLDR

This is the summary text.

## Key Terms
"""
        result = parse_summary(content)
        assert result.tldr == "This is the summary text."

    def test_parse_summary_extracts_key_terms(self):
        """parse_summary extracts key terms."""
        content = """## Key Terms

- **Term One**: Definition one
- **Term Two**: Definition two

## Next Section
"""
        result = parse_summary(content)
        assert len(result.key_terms) == 2
        assert result.key_terms[0] == ("Term One", "Definition one")
        assert result.key_terms[1] == ("Term Two", "Definition two")

    def test_parse_recall_extracts_memory_points(self):
        """parse_recall extracts numbered memory points."""
        content = """## From Memory

*Instructions*

1. First point
2. Second point
3. Third point
4. Fourth point
5. Fifth point

## After Selective Reading
"""
        result = parse_recall(content)
        assert len(result.memory_points) == 5
        assert result.memory_points[0] == "First point"

    def test_parse_recall_pads_to_five_points(self):
        """parse_recall pads to 5 points if fewer exist."""
        content = """## From Memory

*Instructions*

1. Only one point

## After
"""
        result = parse_recall(content)
        assert len(result.memory_points) == 5
        assert result.memory_points[0] == "Only one point"
        assert result.memory_points[1] == ""

    def test_parse_quiz_extracts_questions(self):
        """parse_quiz extracts question data."""
        content = """# Quiz

### 1. Main Claim

What is the main argument?

**Answer:** The main argument is X.

---

### 2. Key Mechanism

What mechanism is described?

A) Option A
B) Option B
C) Option C
D) Option D

**Answer:** B

---
"""
        result = parse_quiz(content)
        assert len(result.questions) == 2
        assert result.questions[0].number == "1"
        assert result.questions[0].title == "Main Claim"
        assert result.questions[0].question_type == "prose"
        assert result.questions[1].question_type == "mcq"
        assert len(result.questions[1].options) == 4

    def test_render_highlights_converts_details_to_tooltips(self):
        """render_answer_with_highlights converts details blocks."""
        answer = 'Some text<details><summary>Error</summary>Feedback here</details>'
        result = render_answer_with_highlights(answer)
        assert 'error-highlight' in result
        assert 'tooltip' in result
        assert 'Error' in result
        assert 'Feedback here' in result


class TestStaticFiles:
    def test_static_css_accessible(self, client):
        """Static CSS file is accessible."""
        response = client.get("/static/styles.css")
        assert response.status_code == 200
        assert "error-highlight" in response.text

    def test_static_js_accessible(self, client):
        """Static JS file is accessible."""
        response = client.get("/static/app.js")
        assert response.status_code == 200
        assert "queueSave" in response.text
