"""Tests for token estimation."""
from edps.core.tokens import estimate_tokens, estimate_cost


def test_estimate_tokens_short_text():
    """Token count for short text is reasonable."""
    text = "Hello, world!"
    tokens = estimate_tokens(text)
    assert 2 <= tokens <= 5  # Should be ~3 tokens


def test_estimate_tokens_longer_text():
    """Token count scales with text length."""
    short = "Hello"
    long = "Hello " * 100

    short_tokens = estimate_tokens(short)
    long_tokens = estimate_tokens(long)

    assert long_tokens > short_tokens * 10
