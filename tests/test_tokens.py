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


def test_estimate_cost_sonnet():
    """Cost estimation for Sonnet model."""
    # 1000 input, 500 output tokens
    cost = estimate_cost(1000, 500, "claude-sonnet-4-20250514")

    # Input: (1000 / 1M) * 3.0 = 0.003
    # Output: (500 / 1M) * 15.0 = 0.0075
    # Total: 0.0105
    assert 0.01 <= cost <= 0.011


def test_estimate_cost_haiku_cheaper():
    """Haiku should be cheaper than Sonnet."""
    sonnet_cost = estimate_cost(1000, 500, "claude-sonnet-4-20250514")
    haiku_cost = estimate_cost(1000, 500, "claude-haiku-3-5")

    assert haiku_cost < sonnet_cost
