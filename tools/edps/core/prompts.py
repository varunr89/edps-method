"""Prompt template management."""
from pathlib import Path
from typing import Any


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt template by name.

    Args:
        name: Prompt name (e.g., "summary", "podcast", "quiz")

    Returns:
        Template string with {placeholders}
    """
    prompt_file = PROMPTS_DIR / f"{name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_file}")

    return prompt_file.read_text(encoding="utf-8")


def render_prompt(template: str, **kwargs: Any) -> str:
    """Render a prompt template with variables.

    Args:
        template: Template string with {placeholders}
        **kwargs: Variables to substitute

    Returns:
        Rendered prompt string
    """
    return template.format(**kwargs)
