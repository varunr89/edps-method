"""Token estimation utilities."""
import tiktoken


# Use cl100k_base encoding (used by Claude)
_encoding = tiktoken.get_encoding("cl100k_base")


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    return len(_encoding.encode(text))


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-sonnet-4-20250514",
) -> float:
    """Estimate cost in USD for API call.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name

    Returns:
        Estimated cost in USD
    """
    # Pricing per 1M tokens (as of Dec 2024)
    pricing = {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-haiku-3-5": {"input": 0.25, "output": 1.25},
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    }

    prices = pricing.get(model, pricing["claude-sonnet-4-20250514"])

    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]

    return input_cost + output_cost
