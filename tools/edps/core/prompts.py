"""Prompt template management.

Loads prompts from a centralized YAML registry (prompts/prompts.yaml).
Supports partials for DRY prompt fragments and versioning.
"""
from pathlib import Path
from typing import Any

import yaml

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
PROMPTS_FILE = PROMPTS_DIR / "prompts.yaml"

_cache: dict | None = None


def _load_registry() -> dict:
    """Load and cache the prompt registry."""
    global _cache
    if _cache is None:
        data = yaml.safe_load(PROMPTS_FILE.read_text(encoding="utf-8"))
        _cache = {
            "partials": data.get("partials", {}),
            "prompts": data.get("prompts", {}),
        }
    return _cache


def _expand_partials(template: str, partials: dict) -> str:
    """Replace {{partial_name}} with partial content."""
    for name, content in partials.items():
        template = template.replace(f"{{{{{name}}}}}", content)
    return template


def load_prompt(name: str) -> str:
    """Load a prompt template by name, expanding partials.

    Args:
        name: Prompt name (e.g., "summary", "quiz", "evaluation")

    Returns:
        Template string with {placeholders} for render_prompt()

    Raises:
        KeyError: If prompt name not found in registry
    """
    registry = _load_registry()

    if name not in registry["prompts"]:
        raise KeyError(f"Prompt '{name}' not found in {PROMPTS_FILE}")

    template = registry["prompts"][name]["template"]
    return _expand_partials(template, registry["partials"])


def get_prompt_version(name: str) -> int:
    """Get the version number of a prompt.

    Args:
        name: Prompt name

    Returns:
        Version number, or 0 if not found
    """
    registry = _load_registry()
    return registry["prompts"].get(name, {}).get("version", 0)


def get_prompt_description(name: str) -> str:
    """Get the description of a prompt.

    Args:
        name: Prompt name

    Returns:
        Description string, or empty if not found
    """
    registry = _load_registry()
    return registry["prompts"].get(name, {}).get("description", "")


def list_prompts() -> list[str]:
    """List all available prompt names.

    Returns:
        List of prompt names
    """
    registry = _load_registry()
    return list(registry["prompts"].keys())


def render_prompt(template: str, **kwargs: Any) -> str:
    """Render a prompt template with variables.

    Args:
        template: Template string with {placeholders}
        **kwargs: Variables to substitute

    Returns:
        Rendered prompt string
    """
    return template.format(**kwargs)


def clear_cache() -> None:
    """Clear the prompt cache. Useful for testing or hot-reloading."""
    global _cache
    _cache = None
