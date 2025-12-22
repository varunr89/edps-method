# EDPS Automation Script Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool that automates EDPS Method artifact generation with Azure AI Foundry.

**Architecture:** Typer CLI with modular commands (`init`, `ingest`, `generate`, `template`, `run`). Core modules handle LLM calls, chunking, and prompts. Confirm-before-execute pattern on all API calls.

**Tech Stack:** Python 3.11+, typer, rich, azure-ai-inference, pyyaml, tiktoken, thefuzz

---

## Phase 1: Project Scaffold & Config

### Task 1.1: Create Package Structure

**Files:**
- Create: `tools/edps/__init__.py`
- Create: `tools/edps/cli.py`
- Create: `tools/edps/config.py`
- Create: `tools/edps/commands/__init__.py`
- Create: `tools/edps/core/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `pyproject.toml`

**Step 1: Create pyproject.toml with dependencies**

```toml
[project]
name = "edps"
version = "0.1.0"
description = "EDPS Method automation CLI"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "tiktoken>=0.5.0",
    "thefuzz>=0.20.0",
    "azure-ai-inference>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]

[project.scripts]
edps = "edps.cli:app"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["tools"]
```

**Step 2: Create package structure with empty __init__.py files**

```bash
mkdir -p tools/edps/commands tools/edps/core tests
touch tools/edps/__init__.py
touch tools/edps/commands/__init__.py
touch tools/edps/core/__init__.py
touch tests/__init__.py
```

**Step 3: Create minimal cli.py**

```python
"""EDPS Method CLI - Main entry point."""
import typer

app = typer.Typer(
    name="edps",
    help="EDPS Method automation CLI",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show version."""
    typer.echo("edps v0.1.0")


if __name__ == "__main__":
    app()
```

**Step 4: Verify CLI runs**

```bash
cd tools && pip install -e ".[dev]" && edps version
```

Expected: `edps v0.1.0`

**Step 5: Commit**

```bash
git add tools/ tests/ pyproject.toml
git commit -m "feat: initialize edps package structure"
```

---

### Task 1.2: Config Module - Load Global Config

**Files:**
- Create: `tools/edps/config.py`
- Create: `tests/test_config.py`

**Step 1: Write failing test for config loading**

```python
# tests/test_config.py
"""Tests for config module."""
import tempfile
from pathlib import Path

import pytest
import yaml

from edps.config import load_config, EdpsConfig


def test_load_config_from_file():
    """Config loads from YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(yaml.dump({
            "azure": {
                "endpoint": "https://test.azure.com",
                "api_key": "test-key",
                "model": "claude-sonnet-4-20250514",
            },
            "defaults": {
                "temperature": 0.3,
                "confirm_before_call": True,
            }
        }))

        config = load_config(config_path)

        assert config.azure.endpoint == "https://test.azure.com"
        assert config.azure.api_key == "test-key"
        assert config.azure.model == "claude-sonnet-4-20250514"
        assert config.defaults.temperature == 0.3
        assert config.defaults.confirm_before_call is True
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py::test_load_config_from_file -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'edps.config'`

**Step 3: Implement config module**

```python
# tools/edps/config.py
"""Configuration management for EDPS CLI."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

import yaml


@dataclass
class AzureConfig:
    """Azure AI Foundry configuration."""
    endpoint: str = ""
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"


@dataclass
class ModelsConfig:
    """Per-task model overrides."""
    chunking: str = "claude-sonnet-4-20250514"
    summary: str = "claude-sonnet-4-20250514"
    podcast: str = "claude-sonnet-4-20250514"
    quiz: str = "claude-haiku-3-5"
    claims_synthesis: str = "claude-sonnet-4-20250514"


@dataclass
class DefaultsConfig:
    """Default settings."""
    temperature: float = 0.3
    max_tokens: int = 4096
    confirm_before_call: bool = True
    cost_warning_threshold: float = 0.50


@dataclass
class EdpsConfig:
    """Root configuration."""
    azure: AzureConfig = field(default_factory=AzureConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)


def load_config(config_path: Optional[Path] = None) -> EdpsConfig:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to ~/.edps/config.yaml

    Returns:
        EdpsConfig with loaded values
    """
    if config_path is None:
        config_path = Path.home() / ".edps" / "config.yaml"

    config = EdpsConfig()

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        # Load azure config
        if "azure" in data:
            azure_data = data["azure"]
            config.azure = AzureConfig(
                endpoint=azure_data.get("endpoint", ""),
                api_key=_resolve_env_var(azure_data.get("api_key", "")),
                model=azure_data.get("model", "claude-sonnet-4-20250514"),
            )

        # Load models config
        if "models" in data:
            models_data = data["models"]
            config.models = ModelsConfig(
                chunking=models_data.get("chunking", config.models.chunking),
                summary=models_data.get("summary", config.models.summary),
                podcast=models_data.get("podcast", config.models.podcast),
                quiz=models_data.get("quiz", config.models.quiz),
                claims_synthesis=models_data.get("claims_synthesis", config.models.claims_synthesis),
            )

        # Load defaults
        if "defaults" in data:
            defaults_data = data["defaults"]
            config.defaults = DefaultsConfig(
                temperature=defaults_data.get("temperature", config.defaults.temperature),
                max_tokens=defaults_data.get("max_tokens", config.defaults.max_tokens),
                confirm_before_call=defaults_data.get("confirm_before_call", config.defaults.confirm_before_call),
                cost_warning_threshold=defaults_data.get("cost_warning_threshold", config.defaults.cost_warning_threshold),
            )

    return config


def _resolve_env_var(value: str) -> str:
    """Resolve ${ENV_VAR} syntax in config values."""
    if value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.environ.get(env_var, "")
    return value
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py::test_load_config_from_file -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/config.py tests/test_config.py
git commit -m "feat: add config module with YAML loading"
```

---

### Task 1.3: Config Module - Environment Variable Resolution

**Files:**
- Modify: `tests/test_config.py`

**Step 1: Write failing test for env var resolution**

```python
# Add to tests/test_config.py
def test_config_resolves_env_vars(monkeypatch):
    """Config resolves ${ENV_VAR} syntax."""
    monkeypatch.setenv("AZURE_AI_API_KEY", "secret-from-env")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text(yaml.dump({
            "azure": {
                "endpoint": "https://test.azure.com",
                "api_key": "${AZURE_AI_API_KEY}",
            }
        }))

        config = load_config(config_path)

        assert config.azure.api_key == "secret-from-env"
```

**Step 2: Run test to verify it passes (already implemented)**

```bash
pytest tests/test_config.py::test_config_resolves_env_vars -v
```

Expected: PASS (already implemented in Task 1.2)

**Step 3: Commit if any changes**

```bash
git add tests/test_config.py
git commit -m "test: add env var resolution test"
```

---

### Task 1.4: Config Module - Save Config

**Files:**
- Modify: `tools/edps/config.py`
- Modify: `tests/test_config.py`

**Step 1: Write failing test for config saving**

```python
# Add to tests/test_config.py
from edps.config import save_config


def test_save_config_creates_file():
    """save_config writes YAML to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        config = EdpsConfig()
        config.azure.endpoint = "https://my-endpoint.azure.com"
        config.azure.api_key = "my-api-key"

        save_config(config, config_path)

        assert config_path.exists()
        loaded = yaml.safe_load(config_path.read_text())
        assert loaded["azure"]["endpoint"] == "https://my-endpoint.azure.com"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py::test_save_config_creates_file -v
```

Expected: FAIL with `cannot import name 'save_config'`

**Step 3: Implement save_config**

```python
# Add to tools/edps/config.py
from dataclasses import asdict


def save_config(config: EdpsConfig, config_path: Optional[Path] = None) -> None:
    """Save configuration to YAML file.

    Args:
        config: Configuration to save
        config_path: Path to save to. Defaults to ~/.edps/config.yaml
    """
    if config_path is None:
        config_path = Path.home() / ".edps" / "config.yaml"

    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "azure": asdict(config.azure),
        "models": asdict(config.models),
        "defaults": asdict(config.defaults),
    }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py::test_save_config_creates_file -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/config.py tests/test_config.py
git commit -m "feat: add save_config function"
```

---

## Phase 2: Init Command

### Task 2.1: Init Command - Basic Structure

**Files:**
- Create: `tools/edps/commands/init.py`
- Modify: `tools/edps/cli.py`
- Create: `tests/test_cmd_init.py`

**Step 1: Write failing test for init command**

```python
# tests/test_cmd_init.py
"""Tests for init command."""
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from edps.cli import app


runner = CliRunner()


def test_init_creates_config_file(monkeypatch):
    """edps init creates config.yaml in specified directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        result = runner.invoke(app, [
            "init",
            "--config-path", str(config_path),
            "--endpoint", "https://test.azure.com",
            "--api-key", "test-key",
            "--no-test-connection",
        ])

        assert result.exit_code == 0
        assert config_path.exists()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cmd_init.py::test_init_creates_config_file -v
```

Expected: FAIL with `No such command 'init'`

**Step 3: Implement init command**

```python
# tools/edps/commands/init.py
"""Init command - configure Azure credentials."""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from edps.config import EdpsConfig, save_config

console = Console()


def init(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config-path",
        help="Path to save config (default: ~/.edps/config.yaml)",
    ),
    endpoint: Optional[str] = typer.Option(
        None,
        "--endpoint",
        help="Azure AI Foundry endpoint URL",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="Azure API key",
    ),
    test_connection: bool = typer.Option(
        True,
        "--test-connection/--no-test-connection",
        help="Test the connection after saving",
    ),
) -> None:
    """Initialize EDPS configuration with Azure credentials."""

    # Interactive prompts if not provided
    if endpoint is None:
        endpoint = Prompt.ask("Azure endpoint")
    if api_key is None:
        api_key = Prompt.ask("API key", password=True)

    # Create config
    config = EdpsConfig()
    config.azure.endpoint = endpoint
    config.azure.api_key = api_key

    # Save
    save_config(config, config_path)

    config_location = config_path or (Path.home() / ".edps" / "config.yaml")
    console.print(f"[green]✓[/green] Config saved to {config_location}")

    # Test connection if requested
    if test_connection:
        console.print("[yellow]Testing connection...[/yellow]")
        # TODO: Implement connection test
        console.print("[yellow]⚠[/yellow] Connection test not yet implemented")
```

**Step 4: Register command in cli.py**

```python
# tools/edps/cli.py
"""EDPS Method CLI - Main entry point."""
import typer

from edps.commands.init import init as init_command

app = typer.Typer(
    name="edps",
    help="EDPS Method automation CLI",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show version."""
    typer.echo("edps v0.1.0")


app.command(name="init")(init_command)


if __name__ == "__main__":
    app()
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_cmd_init.py::test_init_creates_config_file -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add tools/edps/commands/init.py tools/edps/cli.py tests/test_cmd_init.py
git commit -m "feat: add init command for Azure config"
```

---

## Phase 3: LLM Client

### Task 3.1: Token Estimation

**Files:**
- Create: `tools/edps/core/tokens.py`
- Create: `tests/test_tokens.py`

**Step 1: Write failing test for token counting**

```python
# tests/test_tokens.py
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_tokens.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement token estimation**

```python
# tools/edps/core/tokens.py
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_tokens.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/core/tokens.py tests/test_tokens.py
git commit -m "feat: add token estimation utilities"
```

---

### Task 3.2: Cost Estimation Test

**Files:**
- Modify: `tests/test_tokens.py`

**Step 1: Write test for cost estimation**

```python
# Add to tests/test_tokens.py
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
```

**Step 2: Run tests**

```bash
pytest tests/test_tokens.py -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_tokens.py
git commit -m "test: add cost estimation tests"
```

---

### Task 3.3: LLM Client - Basic Structure

**Files:**
- Create: `tools/edps/core/llm.py`
- Create: `tests/test_llm.py`

**Step 1: Write failing test for LLM client creation**

```python
# tests/test_llm.py
"""Tests for LLM client."""
import pytest

from edps.config import EdpsConfig
from edps.core.llm import LLMClient


def test_client_creation():
    """LLMClient can be created with config."""
    config = EdpsConfig()
    config.azure.endpoint = "https://test.azure.com"
    config.azure.api_key = "test-key"

    client = LLMClient(config)

    assert client.endpoint == "https://test.azure.com"
    assert client.default_model == "claude-sonnet-4-20250514"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm.py::test_client_creation -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement LLM client stub**

```python
# tools/edps/core/llm.py
"""Azure AI Foundry LLM client."""
from dataclasses import dataclass
from typing import Optional

from edps.config import EdpsConfig
from edps.core.tokens import estimate_tokens, estimate_cost


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str


@dataclass
class LLMPreview:
    """Preview of what an LLM call will do."""
    prompt: str
    input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float
    model: str


class LLMClient:
    """Client for Azure AI Foundry with Claude models."""

    def __init__(self, config: EdpsConfig):
        """Initialize client with config.

        Args:
            config: EDPS configuration
        """
        self.endpoint = config.azure.endpoint
        self.api_key = config.azure.api_key
        self.default_model = config.azure.model
        self.temperature = config.defaults.temperature
        self.max_tokens = config.defaults.max_tokens
        self._client = None

    def _get_client(self):
        """Lazy-load the Azure client."""
        if self._client is None:
            from azure.ai.inference import ChatCompletionsClient
            from azure.core.credentials import AzureKeyCredential

            self._client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key),
            )
        return self._client

    def preview(
        self,
        prompt: str,
        model: Optional[str] = None,
        estimated_output_tokens: int = 1000,
    ) -> LLMPreview:
        """Preview an LLM call without executing.

        Args:
            prompt: The prompt to send
            model: Model to use (defaults to config)
            estimated_output_tokens: Estimated output size

        Returns:
            LLMPreview with token counts and cost
        """
        model = model or self.default_model
        input_tokens = estimate_tokens(prompt)
        cost = estimate_cost(input_tokens, estimated_output_tokens, model)

        return LLMPreview(
            prompt=prompt,
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimated_cost=cost,
            model=model,
        )

    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Execute an LLM completion.

        Args:
            prompt: The prompt to send
            model: Model to use (defaults to config)
            temperature: Temperature (defaults to config)
            max_tokens: Max tokens (defaults to config)

        Returns:
            LLMResponse with content and usage
        """
        from azure.ai.inference.models import UserMessage

        model = model or self.default_model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens

        client = self._get_client()

        response = client.complete(
            model=model,
            messages=[UserMessage(content=prompt)],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = estimate_cost(input_tokens, output_tokens, model)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model=model,
        )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_llm.py::test_client_creation -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/core/llm.py tests/test_llm.py
git commit -m "feat: add LLM client with preview and complete"
```

---

### Task 3.4: LLM Preview Test

**Files:**
- Modify: `tests/test_llm.py`

**Step 1: Write test for preview functionality**

```python
# Add to tests/test_llm.py
def test_preview_estimates_tokens():
    """preview() estimates tokens without API call."""
    config = EdpsConfig()
    config.azure.endpoint = "https://test.azure.com"
    config.azure.api_key = "test-key"

    client = LLMClient(config)

    preview = client.preview(
        prompt="Summarize this text: " + "word " * 100,
        estimated_output_tokens=500,
    )

    assert preview.input_tokens > 100
    assert preview.estimated_output_tokens == 500
    assert preview.estimated_cost > 0
    assert preview.model == "claude-sonnet-4-20250514"
```

**Step 2: Run test**

```bash
pytest tests/test_llm.py::test_preview_estimates_tokens -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_llm.py
git commit -m "test: add LLM preview test"
```

---

## Phase 4: Confirmation UI

### Task 4.1: Confirmation Prompt

**Files:**
- Create: `tools/edps/core/ui.py`
- Create: `tests/test_ui.py`

**Step 1: Write test for confirmation display**

```python
# tests/test_ui.py
"""Tests for UI components."""
from io import StringIO

from rich.console import Console

from edps.core.llm import LLMPreview
from edps.core.ui import format_preview_panel


def test_format_preview_panel():
    """Preview panel shows key information."""
    preview = LLMPreview(
        prompt="Test prompt...",
        input_tokens=1500,
        estimated_output_tokens=500,
        estimated_cost=0.012,
        model="claude-sonnet-4-20250514",
    )

    output = StringIO()
    console = Console(file=output, force_terminal=True)

    panel = format_preview_panel(
        title="Generate summary.md",
        section="001: Division of Labor",
        preview=preview,
    )
    console.print(panel)

    result = output.getvalue()
    assert "1,500" in result or "1500" in result  # Input tokens
    assert "500" in result  # Output tokens
    assert "0.01" in result  # Cost (formatted)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_ui.py::test_format_preview_panel -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement UI module**

```python
# tools/edps/core/ui.py
"""Terminal UI components."""
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from edps.core.llm import LLMPreview


console = Console()


def format_preview_panel(
    title: str,
    section: str,
    preview: LLMPreview,
) -> Panel:
    """Format a preview panel for confirmation.

    Args:
        title: Action being performed
        section: Section identifier
        preview: LLM call preview

    Returns:
        Rich Panel for display
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")

    table.add_row("Action", title)
    table.add_row("Section", section)
    table.add_row("Model", preview.model)
    table.add_row("Input tokens", f"{preview.input_tokens:,}")
    table.add_row("Est. output", f"{preview.estimated_output_tokens:,}")
    table.add_row("Est. cost", f"${preview.estimated_cost:.4f}")

    return Panel(table, title=section, border_style="blue")


def confirm_action(
    title: str,
    section: str,
    preview: LLMPreview,
    skip_confirm: bool = False,
) -> str:
    """Show preview and get user confirmation.

    Args:
        title: Action being performed
        section: Section identifier
        preview: LLM call preview
        skip_confirm: If True, auto-proceed

    Returns:
        One of: "proceed", "skip", "view", "quit"
    """
    if skip_confirm:
        return "proceed"

    panel = format_preview_panel(title, section, preview)
    console.print(panel)
    console.print()
    console.print("[dim][Enter] Proceed  [s] Skip  [v] View prompt  [q] Quit[/dim]")

    while True:
        choice = console.input("> ").strip().lower()

        if choice == "" or choice == "p" or choice == "proceed":
            return "proceed"
        elif choice == "s" or choice == "skip":
            return "skip"
        elif choice == "v" or choice == "view":
            return "view"
        elif choice == "q" or choice == "quit":
            return "quit"
        else:
            console.print("[red]Invalid choice. Try again.[/red]")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_ui.py::test_format_preview_panel -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/core/ui.py tests/test_ui.py
git commit -m "feat: add confirmation UI components"
```

---

## Phase 5: Chunking

### Task 5.1: Regex Chapter Detection

**Files:**
- Create: `tools/edps/core/chunker.py`
- Create: `tests/test_chunker.py`

**Step 1: Write failing test for regex chapter detection**

```python
# tests/test_chunker.py
"""Tests for text chunking."""
from edps.core.chunker import find_chapter_markers


def test_find_chapter_markers_standard():
    """Detects 'CHAPTER X' format."""
    text = """
CHAPTER I.
OF THE DIVISION OF LABOUR.

The greatest improvement in the productive powers...

CHAPTER II.
OF THE PRINCIPLE WHICH GIVES OCCASION TO THE DIVISION OF LABOUR.

This division of labour...

CHAPTER III.
THAT THE DIVISION OF LABOUR IS LIMITED BY THE EXTENT OF THE MARKET.

As it is the power...
"""

    markers = find_chapter_markers(text)

    assert len(markers) == 3
    assert markers[0]["title"] == "OF THE DIVISION OF LABOUR"
    assert markers[1]["title"] == "OF THE PRINCIPLE WHICH GIVES OCCASION TO THE DIVISION OF LABOUR"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_chunker.py::test_find_chapter_markers_standard -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement chapter detection**

```python
# tools/edps/core/chunker.py
"""Text chunking utilities."""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ChapterMarker:
    """A detected chapter/section marker."""
    number: str
    title: str
    start_pos: int


@dataclass
class Section:
    """A chunked section of text."""
    id: str
    title: str
    location: str
    start_byte: int
    end_byte: int
    word_count: int
    text: str


# Patterns to try in order
CHAPTER_PATTERNS = [
    # CHAPTER I. or CHAPTER 1.
    r'^CHAPTER\s+([IVXLCDM]+|\d+)\.?\s*\n+([A-Z][^\n]+)',
    # Chapter 1: Title
    r'^Chapter\s+(\d+):\s*([^\n]+)',
    # BOOK I or Book I
    r'^BOOK\s+([IVXLCDM]+|\d+)\.?\s*\n+([A-Z][^\n]+)',
    # Part I or PART I
    r'^(?:PART|Part)\s+([IVXLCDM]+|\d+)\.?\s*\n+([A-Z][^\n]+)',
    # Section 1 or § 1
    r'^(?:Section|§)\s*(\d+)\.?\s*([^\n]*)',
]


def find_chapter_markers(text: str) -> List[dict]:
    """Find chapter/section markers in text using regex.

    Args:
        text: Full book text

    Returns:
        List of dicts with 'number', 'title', 'start_pos'
    """
    markers = []

    for pattern in CHAPTER_PATTERNS:
        for match in re.finditer(pattern, text, re.MULTILINE):
            number = match.group(1).strip()
            title = match.group(2).strip() if match.lastindex >= 2 else ""

            # Clean up title (remove trailing punctuation)
            title = re.sub(r'[.\s]+$', '', title)

            markers.append({
                "number": number,
                "title": title,
                "start_pos": match.start(),
            })

        # If we found markers with this pattern, stop trying others
        if markers:
            break

    # Sort by position
    markers.sort(key=lambda m: m["start_pos"])

    return markers


def chunk_by_markers(
    text: str,
    markers: List[dict],
    target_words: int = 2500,
    min_words: int = 1500,
    max_words: int = 4000,
) -> List[Section]:
    """Chunk text into sections based on markers.

    Args:
        text: Full book text
        markers: Chapter markers from find_chapter_markers
        target_words: Target words per section
        min_words: Minimum words per section (merge if smaller)
        max_words: Maximum words per section (split if larger)

    Returns:
        List of Section objects
    """
    if not markers:
        return []

    sections = []
    section_num = 1

    for i, marker in enumerate(markers):
        start = marker["start_pos"]

        # End is either next marker or end of text
        if i + 1 < len(markers):
            end = markers[i + 1]["start_pos"]
        else:
            end = len(text)

        section_text = text[start:end]
        word_count = len(section_text.split())

        section = Section(
            id=f"{section_num:03d}",
            title=marker["title"],
            location=f"Chapter {marker['number']}",
            start_byte=start,
            end_byte=end,
            word_count=word_count,
            text=section_text,
        )

        sections.append(section)
        section_num += 1

    return sections
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_chunker.py::test_find_chapter_markers_standard -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/core/chunker.py tests/test_chunker.py
git commit -m "feat: add regex chapter detection"
```

---

### Task 5.2: Chunk by Markers Test

**Files:**
- Modify: `tests/test_chunker.py`

**Step 1: Write test for chunking**

```python
# Add to tests/test_chunker.py
from edps.core.chunker import chunk_by_markers


def test_chunk_by_markers():
    """chunk_by_markers creates Section objects."""
    text = """
CHAPTER I.
OF THE DIVISION OF LABOUR.

The greatest improvement in the productive powers of labour...
This is the first chapter content with many words.

CHAPTER II.
OF THE PRINCIPLE WHICH GIVES OCCASION TO THE DIVISION OF LABOUR.

This division of labour, from which so many advantages are derived...
Second chapter content here.
"""

    markers = find_chapter_markers(text)
    sections = chunk_by_markers(text, markers)

    assert len(sections) == 2
    assert sections[0].id == "001"
    assert sections[0].title == "OF THE DIVISION OF LABOUR"
    assert sections[0].location == "Chapter I"
    assert sections[0].word_count > 0
    assert "greatest improvement" in sections[0].text
```

**Step 2: Run test**

```bash
pytest tests/test_chunker.py::test_chunk_by_markers -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_chunker.py
git commit -m "test: add chunk_by_markers test"
```

---

## Phase 6: Ingest Command

### Task 6.1: Ingest Command - Basic Structure

**Files:**
- Create: `tools/edps/commands/ingest.py`
- Modify: `tools/edps/cli.py`
- Create: `tests/test_cmd_ingest.py`

**Step 1: Write failing test for ingest command**

```python
# tests/test_cmd_ingest.py
"""Tests for ingest command."""
import tempfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from edps.cli import app


runner = CliRunner()


def test_ingest_creates_sections_yaml(monkeypatch):
    """edps ingest creates sections.yaml from raw text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create books_raw with test book
        raw_dir = tmpdir / "books_raw"
        raw_dir.mkdir()
        (raw_dir / "test-book.txt").write_text("""
CHAPTER I.
THE FIRST CHAPTER.

This is the content of the first chapter. It contains many words
to make it seem like a real chapter with substantial content.

CHAPTER II.
THE SECOND CHAPTER.

This is the content of the second chapter. Also with enough words
to be considered a reasonable chapter length.
""")

        # Create books directory
        books_dir = tmpdir / "books"
        books_dir.mkdir()

        # Run ingest
        result = runner.invoke(app, [
            "ingest", "test-book",
            "--books-raw", str(raw_dir),
            "--books-dir", str(books_dir),
            "--yes",  # Skip confirmations
        ])

        assert result.exit_code == 0, result.output

        # Check sections.yaml created
        sections_path = books_dir / "test-book" / "sections.yaml"
        assert sections_path.exists()

        sections = yaml.safe_load(sections_path.read_text())
        assert "sections" in sections
        assert len(sections["sections"]) == 2
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cmd_ingest.py::test_ingest_creates_sections_yaml -v
```

Expected: FAIL with `No such command 'ingest'`

**Step 3: Implement ingest command**

```python
# tools/edps/commands/ingest.py
"""Ingest command - parse raw text and create sections."""
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from edps.core.chunker import find_chapter_markers, chunk_by_markers

console = Console()


def ingest(
    book_slug: str = typer.Argument(..., help="Book slug (e.g., 'wealth-of-nations')"),
    books_raw: Optional[Path] = typer.Option(
        None,
        "--books-raw",
        help="Path to books_raw directory",
    ),
    books_dir: Optional[Path] = typer.Option(
        None,
        "--books-dir",
        help="Path to books directory",
    ),
    yes: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Skip confirmation prompts",
    ),
) -> None:
    """Ingest a book from books_raw and create section structure."""

    # Default paths
    if books_raw is None:
        books_raw = Path.cwd() / "books_raw"
    if books_dir is None:
        books_dir = Path.cwd() / "books"

    # Find raw text file
    raw_file = books_raw / f"{book_slug}.txt"
    if not raw_file.exists():
        # Try with .txt.utf-8 extension
        raw_file = books_raw / f"{book_slug}.txt.utf-8"

    if not raw_file.exists():
        console.print(f"[red]Error:[/red] Raw text not found: {raw_file}")
        raise typer.Exit(1)

    console.print(f"[blue]Reading:[/blue] {raw_file}")
    text = raw_file.read_text(encoding="utf-8")

    # Find chapter markers
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Finding chapter markers...", total=None)
        markers = find_chapter_markers(text)

    if not markers:
        console.print("[red]Error:[/red] No chapter markers found")
        console.print("[dim]Tried patterns: CHAPTER X, Chapter X, BOOK X, Part X, Section X[/dim]")
        raise typer.Exit(1)

    console.print(f"[green]Found {len(markers)} chapters[/green]")

    # Chunk by markers
    sections = chunk_by_markers(text, markers)

    # Show preview
    console.print()
    console.print("[bold]Proposed sections:[/bold]")
    for s in sections[:5]:
        console.print(f"  {s.id}: {s.title[:50]}... ({s.word_count:,} words)")
    if len(sections) > 5:
        console.print(f"  ... and {len(sections) - 5} more")

    # Confirm
    if not yes:
        if not typer.confirm("\nProceed with these sections?"):
            raise typer.Abort()

    # Create book directory
    book_dir = books_dir / book_slug
    book_dir.mkdir(parents=True, exist_ok=True)

    sections_dir = book_dir / "sections"
    sections_dir.mkdir(exist_ok=True)

    # Write sections.yaml
    sections_data = {
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "location": s.location,
                "start_byte": s.start_byte,
                "end_byte": s.end_byte,
                "word_count": s.word_count,
            }
            for s in sections
        ]
    }

    sections_yaml = book_dir / "sections.yaml"
    with open(sections_yaml, "w") as f:
        yaml.dump(sections_data, f, default_flow_style=False, allow_unicode=True)

    console.print(f"[green]✓[/green] Created {sections_yaml}")

    # Write source.txt for each section
    for s in sections:
        section_dir = sections_dir / s.id
        section_dir.mkdir(exist_ok=True)

        source_file = section_dir / "source.txt"
        source_file.write_text(s.text, encoding="utf-8")

    console.print(f"[green]✓[/green] Created {len(sections)} source.txt files")

    # Create meta.yaml if it doesn't exist
    meta_path = book_dir / "meta.yaml"
    if not meta_path.exists():
        meta_data = {
            "title": book_slug.replace("-", " ").title(),
            "status": "planned",
        }
        with open(meta_path, "w") as f:
            yaml.dump(meta_data, f, default_flow_style=False)
        console.print(f"[green]✓[/green] Created {meta_path}")
```

**Step 4: Register command in cli.py**

```python
# Modify tools/edps/cli.py - add import and registration
from edps.commands.ingest import ingest as ingest_command

# Add after init registration:
app.command(name="ingest")(ingest_command)
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_cmd_ingest.py::test_ingest_creates_sections_yaml -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add tools/edps/commands/ingest.py tools/edps/cli.py tests/test_cmd_ingest.py
git commit -m "feat: add ingest command for book chunking"
```

---

### Task 6.2: Ingest Creates Source Files

**Files:**
- Modify: `tests/test_cmd_ingest.py`

**Step 1: Write test for source.txt creation**

```python
# Add to tests/test_cmd_ingest.py
def test_ingest_creates_source_files(monkeypatch):
    """edps ingest creates source.txt for each section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        raw_dir = tmpdir / "books_raw"
        raw_dir.mkdir()
        (raw_dir / "test-book.txt").write_text("""
CHAPTER I.
FIRST CHAPTER TITLE.

First chapter content here.

CHAPTER II.
SECOND CHAPTER TITLE.

Second chapter content here.
""")

        books_dir = tmpdir / "books"
        books_dir.mkdir()

        result = runner.invoke(app, [
            "ingest", "test-book",
            "--books-raw", str(raw_dir),
            "--books-dir", str(books_dir),
            "--yes",
        ])

        assert result.exit_code == 0

        # Check source files created
        source_001 = books_dir / "test-book" / "sections" / "001" / "source.txt"
        source_002 = books_dir / "test-book" / "sections" / "002" / "source.txt"

        assert source_001.exists()
        assert source_002.exists()
        assert "First chapter content" in source_001.read_text()
```

**Step 2: Run test**

```bash
pytest tests/test_cmd_ingest.py::test_ingest_creates_source_files -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_cmd_ingest.py
git commit -m "test: verify ingest creates source.txt files"
```

---

## Phase 7: Prompts

### Task 7.1: Prompt Templates

**Files:**
- Create: `tools/edps/prompts/summary.txt`
- Create: `tools/edps/prompts/podcast.txt`
- Create: `tools/edps/prompts/quiz.txt`
- Create: `tools/edps/core/prompts.py`
- Create: `tests/test_prompts.py`

**Step 1: Create prompt template files**

```text
# tools/edps/prompts/summary.txt
You are analyzing a section from "{book_title}" by {author}.

## Section Details
- Section: {section_id}
- Title: {section_title}
- Location: {location}

## Source Text
{source_text}

## Task
Generate a structured summary following this EXACT format:

---

# Section {section_id}: {section_title}

> Location: {location}
> Generator: 🤖 AI-generated
> Last updated: {date}

---

## TLDR

[Write exactly 3 sentences summarizing the core claim.]

---

## Key Terms

- **[Term 1]**: [definition as used in this text]
- **[Term 2]**: [definition]
- **[Term 3]**: [definition]
- **[Term 4]**: [definition]
- **[Term 5]**: [definition]

---

## Argument Structure

1. [First premise or observation from the text]
2. [Second step in the author's reasoning]
3. [Third step]
4. [Fourth step]
5. [Conclusion or implication]

---

## Modern Application

[Write 3-5 sentences connecting this to something from the last 10 years: policy, technology, markets, or society. Be specific.]

---

## Source Pointers

- **Key passage**: [quote a key sentence and its approximate location]
- **Best example**: [describe the author's main example]
- **Strongest argument**: [identify the most compelling point]

---

## Generation Notes

- Model: {model}
- Prompt version: 1.0
- Human edits: none
```

```text
# tools/edps/prompts/podcast.txt
You are creating a podcast script about a section from "{book_title}" by {author}.

## Section Details
- Section: {section_id}
- Title: {section_title}
- Location: {location}

## Summary (for context)
{summary_text}

## Source Text
{source_text}

## Task
Create an 8-12 minute podcast script with two speakers:
- **Host**: Curious, asks clarifying questions, makes modern parallels
- **Analyst**: Expert, explains arguments, gives examples from the text

Follow this EXACT format:

---

# Episode {section_id}: {section_title}

> Duration target: 8-12 minutes
> Generator: 🤖 AI-generated
> Last updated: {date}

---

## Speakers

- **Host**: Sets context, asks questions, summarizes. Curious but not expert.
- **Analyst**: Explains arguments, gives examples, corrects misconceptions. Expert voice.

---

## Script

**[HOST]**: [Opening hook - why this matters to a modern listener, 2-3 sentences]

**[ANALYST]**: [Core claim in plain language]

**[HOST]**: [Clarifying question]

**[ANALYST]**: [Deeper explanation with example FROM THE TEXT]

**[HOST]**: [Modern parallel - "So this is kind of like..."]

**[ANALYST]**: [Confirm or correct the parallel]

**[HOST]**: [Potential objection]

**[ANALYST]**: [Address the objection]

**[HOST]**: [Recap - "So the key takeaway is..."]

**[ANALYST]**: [Confirm + one additional nuance]

---

## Closing Questions

1. **Recall**: [Factual question]
2. **Understand**: [Conceptual question]
3. **Apply**: [Modern connection question]

---

## Production Notes

- **Historical example used**: [brief description]
- **Modern parallel used**: [brief description]
- **Estimated read time**: [X minutes at natural pace]
```

```text
# tools/edps/prompts/quiz.txt
You are creating retrieval practice questions for a section from "{book_title}" by {author}.

## Section Details
- Section: {section_id}
- Title: {section_title}
- Location: {location}

## Summary
{summary_text}

## Source Text
{source_text}

## Task
Create exactly 8 questions following this format:

---

# Quiz: Section {section_id}

> Generator: 🤖 AI-generated
> Total questions: 8
> Time estimate: 10-15 minutes

---

## Instructions

1. Answer all questions **from memory** — no peeking at notes or source
2. Write your answers in `quiz-answers.md`
3. Score yourself after completing all questions

---

## Recall Questions

*Answer each in 1-2 sentences.*

### 1. Main Claim
[Ask about the central argument]

### 2. Mechanism
[Ask about a process or cause-effect relationship]

### 3. Example
[Ask about an example from the text]

### 4. Define: [Key Term 1]
[Ask for definition of first key term]

### 5. Define: [Key Term 2]
[Ask for definition of second key term]

---

## Explain Questions

*Answer each in 3-5 sentences.*

### 6. Teach It Back
[Ask to explain a concept to a smart 15-year-old]

### 7. Counterfactual
[Ask what would happen if a key condition were different]

---

## Apply Question

*Answer in 3-5 sentences.*

### 8. Modern Connection
[Ask to connect a concept to a specific modern phenomenon]
```

**Step 2: Write test for prompt loading**

```python
# tests/test_prompts.py
"""Tests for prompt templates."""
from edps.core.prompts import load_prompt, render_prompt


def test_load_prompt_summary():
    """Can load summary prompt template."""
    template = load_prompt("summary")

    assert "{book_title}" in template
    assert "{source_text}" in template
    assert "TLDR" in template


def test_render_prompt():
    """render_prompt substitutes variables."""
    template = "Hello {name}, your book is {book_title}."

    result = render_prompt(template, name="Alice", book_title="Test Book")

    assert result == "Hello Alice, your book is Test Book."
```

**Step 3: Implement prompts module**

```python
# tools/edps/core/prompts.py
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
```

**Step 4: Create prompts directory and files**

```bash
mkdir -p tools/edps/prompts
# Write the prompt files shown above
```

**Step 5: Run tests**

```bash
pytest tests/test_prompts.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add tools/edps/prompts/ tools/edps/core/prompts.py tests/test_prompts.py
git commit -m "feat: add prompt templates for summary, podcast, quiz"
```

---

## Phase 8: Generate Command

### Task 8.1: Generate Command - Single Section Summary

**Files:**
- Create: `tools/edps/commands/generate.py`
- Modify: `tools/edps/cli.py`
- Create: `tests/test_cmd_generate.py`

**Step 1: Write test for generate command (mocked LLM)**

```python
# tests/test_cmd_generate.py
"""Tests for generate command."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml
from typer.testing import CliRunner

from edps.cli import app
from edps.core.llm import LLMResponse


runner = CliRunner()


def test_generate_creates_summary(monkeypatch):
    """edps generate creates summary.md for a section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup book structure
        book_dir = tmpdir / "books" / "test-book"
        section_dir = book_dir / "sections" / "001"
        section_dir.mkdir(parents=True)

        # Create sections.yaml
        (book_dir / "sections.yaml").write_text(yaml.dump({
            "sections": [{
                "id": "001",
                "title": "Test Chapter",
                "location": "Chapter 1",
                "word_count": 500,
            }]
        }))

        # Create meta.yaml
        (book_dir / "meta.yaml").write_text(yaml.dump({
            "title": "Test Book",
            "author": "Test Author",
        }))

        # Create source.txt
        (section_dir / "source.txt").write_text("This is the chapter content.")

        # Create config
        config_dir = tmpdir / ".edps"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(yaml.dump({
            "azure": {
                "endpoint": "https://test.azure.com",
                "api_key": "test-key",
            }
        }))

        # Mock LLM response
        mock_response = LLMResponse(
            content="# Section 001: Test Chapter\n\n## TLDR\n\nThis is a test summary.",
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
            MockClient.return_value = mock_client

            result = runner.invoke(app, [
                "generate", "test-book", "001",
                "--books-dir", str(tmpdir / "books"),
                "--config-path", str(config_dir / "config.yaml"),
                "--yes",
                "--type", "summary",
            ])

        assert result.exit_code == 0, result.output

        summary_path = section_dir / "summary.md"
        assert summary_path.exists()
        assert "TLDR" in summary_path.read_text()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cmd_generate.py::test_generate_creates_summary -v
```

Expected: FAIL with `No such command 'generate'`

**Step 3: Implement generate command**

```python
# tools/edps/commands/generate.py
"""Generate command - create AI content for sections."""
from datetime import date
from pathlib import Path
from typing import Optional, List

import typer
import yaml
from rich.console import Console

from edps.config import load_config
from edps.core.llm import LLMClient
from edps.core.prompts import load_prompt, render_prompt
from edps.core.ui import confirm_action

console = Console()


def generate(
    book_slug: str = typer.Argument(..., help="Book slug"),
    section_id: Optional[str] = typer.Argument(None, help="Section ID (e.g., '001'). If omitted, generates all."),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir", help="Path to books directory"),
    config_path: Optional[Path] = typer.Option(None, "--config-path", help="Path to config file"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
    gen_type: str = typer.Option("all", "--type", "-t", help="Type to generate: summary, podcast, quiz, or all"),
) -> None:
    """Generate AI content for book sections."""

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

    # Filter to specific section if requested
    if section_id:
        sections = [s for s in sections if s["id"] == section_id]
        if not sections:
            console.print(f"[red]Error:[/red] Section not found: {section_id}")
            raise typer.Exit(1)

    # Create LLM client
    client = LLMClient(config)

    # Determine what to generate
    types_to_generate = []
    if gen_type == "all":
        types_to_generate = ["summary", "podcast", "quiz"]
    else:
        types_to_generate = [gen_type]

    # Generate for each section
    for section in sections:
        section_dir = book_dir / "sections" / section["id"]
        source_path = section_dir / "source.txt"

        if not source_path.exists():
            console.print(f"[yellow]Warning:[/yellow] No source.txt for section {section['id']}, skipping")
            continue

        source_text = source_path.read_text(encoding="utf-8")

        for gen_type_item in types_to_generate:
            output_path = section_dir / f"{gen_type_item}.md"

            # Skip if already exists
            if output_path.exists():
                console.print(f"[dim]Skipping {section['id']}/{gen_type_item}.md (exists)[/dim]")
                continue

            # Generate
            result = _generate_content(
                client=client,
                gen_type=gen_type_item,
                section=section,
                source_text=source_text,
                meta=meta,
                section_dir=section_dir,
                skip_confirm=yes,
            )

            if result == "quit":
                raise typer.Exit(0)
            elif result == "skip":
                continue

            console.print(f"[green]✓[/green] Created {output_path}")


def _generate_content(
    client: LLMClient,
    gen_type: str,
    section: dict,
    source_text: str,
    meta: dict,
    section_dir: Path,
    skip_confirm: bool,
) -> str:
    """Generate a single piece of content.

    Returns: "done", "skip", or "quit"
    """
    # Load and render prompt
    template = load_prompt(gen_type)

    # For podcast and quiz, we need the summary
    summary_text = ""
    if gen_type in ["podcast", "quiz"]:
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
            # Re-prompt after viewing
            return _generate_content(client, gen_type, section, source_text, meta, section_dir, skip_confirm)

    # Execute
    response = client.complete(prompt)

    # Save
    output_path = section_dir / f"{gen_type}.md"
    output_path.write_text(response.content, encoding="utf-8")

    console.print(f"[dim]Tokens: {response.input_tokens} in, {response.output_tokens} out. Cost: ${response.cost:.4f}[/dim]")

    return "done"
```

**Step 4: Register in cli.py**

```python
# Add to tools/edps/cli.py
from edps.commands.generate import generate as generate_command

app.command(name="generate")(generate_command)
```

**Step 5: Run test**

```bash
pytest tests/test_cmd_generate.py::test_generate_creates_summary -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add tools/edps/commands/generate.py tools/edps/cli.py tests/test_cmd_generate.py
git commit -m "feat: add generate command for AI content creation"
```

---

## Phase 9: Template Command

### Task 9.1: Template Command - Create Human Templates

**Files:**
- Create: `tools/edps/commands/template.py`
- Modify: `tools/edps/cli.py`
- Create: `tests/test_cmd_template.py`

**Step 1: Write test for template command**

```python
# tests/test_cmd_template.py
"""Tests for template command."""
import tempfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from edps.cli import app


runner = CliRunner()


def test_template_creates_recall_md():
    """edps template creates recall.md for sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup book structure
        book_dir = tmpdir / "books" / "test-book"
        section_dir = book_dir / "sections" / "001"
        section_dir.mkdir(parents=True)

        (book_dir / "sections.yaml").write_text(yaml.dump({
            "sections": [{"id": "001", "title": "Test Chapter"}]
        }))

        result = runner.invoke(app, [
            "template", "test-book",
            "--books-dir", str(tmpdir / "books"),
        ])

        assert result.exit_code == 0

        recall_path = section_dir / "recall.md"
        assert recall_path.exists()
        assert "<!-- TEMPLATE" in recall_path.read_text()
        assert "From Memory" in recall_path.read_text()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cmd_template.py::test_template_creates_recall_md -v
```

Expected: FAIL

**Step 3: Implement template command**

```python
# tools/edps/commands/template.py
"""Template command - create human-writable templates."""
from datetime import date
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

console = Console()


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


QUIZ_ANSWERS_TEMPLATE = """<!-- TEMPLATE: Fill in your answers below -->
# Quiz Answers: Section {section_id}

> Section: {title}
> Date: {date}

---

## Recall Questions

### 1. Main Claim
[Your answer]

### 2. Mechanism
[Your answer]

### 3. Example
[Your answer]

### 4. Define: [Term 1]
[Your answer]

### 5. Define: [Term 2]
[Your answer]

---

## Explain Questions

### 6. Teach It Back
[Your answer - 3-5 sentences]

### 7. Counterfactual
[Your answer - 3-5 sentences]

---

## Apply Question

### 8. Modern Connection
[Your answer - 3-5 sentences]

---

## Score

- Recall (1-5): __ / 5
- Explain (6-7): __ / 3
- Apply (8): __ / 2
- **Total: __ / 10**
"""


def template(
    book_slug: str = typer.Argument(..., help="Book slug"),
    section_id: Optional[str] = typer.Argument(None, help="Section ID (if omitted, all sections)"),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir", help="Path to books directory"),
) -> None:
    """Create human-writable template files for sections."""

    if books_dir is None:
        books_dir = Path.cwd() / "books"

    book_dir = books_dir / book_slug
    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Book not found: {book_dir}")
        raise typer.Exit(1)

    # Load sections
    sections_path = book_dir / "sections.yaml"
    if not sections_path.exists():
        console.print("[red]Error:[/red] sections.yaml not found")
        raise typer.Exit(1)

    sections_data = yaml.safe_load(sections_path.read_text())
    sections = sections_data.get("sections", [])

    if section_id:
        sections = [s for s in sections if s["id"] == section_id]

    created_count = 0

    for section in sections:
        section_dir = book_dir / "sections" / section["id"]
        section_dir.mkdir(parents=True, exist_ok=True)

        # Create recall.md
        recall_path = section_dir / "recall.md"
        if not recall_path.exists():
            content = RECALL_TEMPLATE.format(
                section_id=section["id"],
                title=section.get("title", ""),
                date=date.today().isoformat(),
            )
            recall_path.write_text(content)
            created_count += 1

        # Create quiz-answers.md
        answers_path = section_dir / "quiz-answers.md"
        if not answers_path.exists():
            content = QUIZ_ANSWERS_TEMPLATE.format(
                section_id=section["id"],
                title=section.get("title", ""),
                date=date.today().isoformat(),
            )
            answers_path.write_text(content)
            created_count += 1

    console.print(f"[green]✓[/green] Created {created_count} template files")
```

**Step 4: Register in cli.py**

```python
# Add to tools/edps/cli.py
from edps.commands.template import template as template_command

app.command(name="template")(template_command)
```

**Step 5: Run test**

```bash
pytest tests/test_cmd_template.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add tools/edps/commands/template.py tools/edps/cli.py tests/test_cmd_template.py
git commit -m "feat: add template command for human-writable files"
```

---

## Phase 10: Interactive Runner

### Task 10.1: Run Command - State Detection

**Files:**
- Create: `tools/edps/commands/run.py`
- Create: `tools/edps/core/state.py`
- Create: `tests/test_state.py`

**Step 1: Write test for state detection**

```python
# tests/test_state.py
"""Tests for state detection."""
import tempfile
from pathlib import Path

import yaml

from edps.core.state import detect_book_state, BookState


def test_detect_state_no_sections():
    """No sections.yaml means not ingested."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir) / "test-book"
        book_dir.mkdir()

        state = detect_book_state(book_dir)

        assert state.ingested is False
        assert state.total_sections == 0


def test_detect_state_with_sections():
    """With sections.yaml, counts what's generated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        book_dir = Path(tmpdir) / "test-book"
        book_dir.mkdir()

        # Create sections.yaml
        (book_dir / "sections.yaml").write_text(yaml.dump({
            "sections": [
                {"id": "001", "title": "First"},
                {"id": "002", "title": "Second"},
                {"id": "003", "title": "Third"},
            ]
        }))

        # Create some generated files
        section_001 = book_dir / "sections" / "001"
        section_001.mkdir(parents=True)
        (section_001 / "source.txt").write_text("content")
        (section_001 / "summary.md").write_text("summary")

        section_002 = book_dir / "sections" / "002"
        section_002.mkdir(parents=True)
        (section_002 / "source.txt").write_text("content")

        state = detect_book_state(book_dir)

        assert state.ingested is True
        assert state.total_sections == 3
        assert state.summaries_done == 1
        assert state.podcasts_done == 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_state.py -v
```

Expected: FAIL

**Step 3: Implement state detection**

```python
# tools/edps/core/state.py
"""Book state detection."""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class BookState:
    """Current state of a book's processing."""
    ingested: bool
    total_sections: int
    summaries_done: int
    podcasts_done: int
    quizzes_done: int
    templates_done: int
    claims_map_done: bool
    next_section: Optional[str]
    pending_sections: List[str]


def detect_book_state(book_dir: Path) -> BookState:
    """Detect current processing state for a book.

    Args:
        book_dir: Path to book directory

    Returns:
        BookState with counts and next actions
    """
    sections_path = book_dir / "sections.yaml"

    if not sections_path.exists():
        return BookState(
            ingested=False,
            total_sections=0,
            summaries_done=0,
            podcasts_done=0,
            quizzes_done=0,
            templates_done=0,
            claims_map_done=False,
            next_section=None,
            pending_sections=[],
        )

    sections_data = yaml.safe_load(sections_path.read_text())
    sections = sections_data.get("sections", [])

    summaries_done = 0
    podcasts_done = 0
    quizzes_done = 0
    templates_done = 0
    pending = []

    for section in sections:
        section_dir = book_dir / "sections" / section["id"]

        has_summary = (section_dir / "summary.md").exists()
        has_podcast = (section_dir / "podcast.md").exists()
        has_quiz = (section_dir / "quiz.md").exists()
        has_recall = (section_dir / "recall.md").exists()

        if has_summary:
            summaries_done += 1
        if has_podcast:
            podcasts_done += 1
        if has_quiz:
            quizzes_done += 1
        if has_recall:
            templates_done += 1

        if not (has_summary and has_podcast and has_quiz):
            pending.append(section["id"])

    claims_map_done = (book_dir / "claims-map.md").exists()

    return BookState(
        ingested=True,
        total_sections=len(sections),
        summaries_done=summaries_done,
        podcasts_done=podcasts_done,
        quizzes_done=quizzes_done,
        templates_done=templates_done,
        claims_map_done=claims_map_done,
        next_section=pending[0] if pending else None,
        pending_sections=pending,
    )
```

**Step 4: Run test**

```bash
pytest tests/test_state.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add tools/edps/core/state.py tests/test_state.py
git commit -m "feat: add book state detection"
```

---

### Task 10.2: Run Command - Main Menu

**Files:**
- Create: `tools/edps/commands/run.py`
- Modify: `tools/edps/cli.py`

**Step 1: Implement run command**

```python
# tools/edps/commands/run.py
"""Run command - interactive workflow runner."""
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from edps.config import load_config
from edps.core.state import detect_book_state
from edps.commands.generate import generate
from edps.commands.template import template

console = Console()


def run(
    book_slug: str = typer.Argument(..., help="Book slug"),
    books_dir: Optional[Path] = typer.Option(None, "--books-dir"),
    config_path: Optional[Path] = typer.Option(None, "--config-path"),
) -> None:
    """Interactive workflow runner for EDPS Method."""

    if books_dir is None:
        books_dir = Path.cwd() / "books"

    book_dir = books_dir / book_slug
    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Book not found: {book_dir}")
        raise typer.Exit(1)

    # Load metadata
    meta_path = book_dir / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
    else:
        meta = {"title": book_slug}

    while True:
        # Detect state
        state = detect_book_state(book_dir)

        # Show header
        console.clear()
        console.print(Panel(
            f"[bold]{meta.get('title', book_slug)}[/bold]\n"
            f"{meta.get('author', 'Unknown')}, {meta.get('year', '')}\n\n"
            f"Status: {state.total_sections} sections, "
            f"{state.summaries_done} summaries, "
            f"{state.podcasts_done} podcasts, "
            f"{state.quizzes_done} quizzes",
            title="EDPS Method",
            border_style="blue",
        ))

        # Build menu options
        options = []

        if not state.ingested:
            console.print("\n[yellow]Book not ingested. Run 'edps ingest' first.[/yellow]")
            break

        if state.pending_sections:
            options.append(f"[1] Continue generating ({len(state.pending_sections)} pending)")

        if state.summaries_done > 0:
            options.append("[2] Review existing outputs")

        options.append("[3] Regenerate a specific section")

        if state.summaries_done > 0:
            options.append("[4] Generate templates (recall.md, quiz-answers.md)")

        options.append("[5] View cost summary")
        options.append("[q] Quit")

        console.print("\nWhat would you like to do?\n")
        for opt in options:
            console.print(f"  {opt}")

        choice = Prompt.ask("\n>", default="1")

        if choice == "q" or choice == "quit":
            break
        elif choice == "1" and state.pending_sections:
            # Continue generating
            generate(
                book_slug=book_slug,
                section_id=None,
                books_dir=books_dir,
                config_path=config_path,
                yes=False,
                gen_type="all",
            )
        elif choice == "3":
            section_id = Prompt.ask("Section ID")
            gen_type = Prompt.ask("Type (summary/podcast/quiz/all)", default="all")
            generate(
                book_slug=book_slug,
                section_id=section_id,
                books_dir=books_dir,
                config_path=config_path,
                yes=False,
                gen_type=gen_type,
            )
        elif choice == "4":
            template(
                book_slug=book_slug,
                section_id=None,
                books_dir=books_dir,
            )
        elif choice == "5":
            console.print("\n[dim]Cost tracking not yet implemented[/dim]")
            Prompt.ask("Press Enter to continue")

        # Pause before loop
        if choice not in ["q", "quit"]:
            Prompt.ask("\nPress Enter to continue")
```

**Step 2: Register in cli.py**

```python
# Add to tools/edps/cli.py
from edps.commands.run import run as run_command

app.command(name="run")(run_command)
```

**Step 3: Manual test**

```bash
edps run wealth-of-nations --books-dir ./books
```

**Step 4: Commit**

```bash
git add tools/edps/commands/run.py tools/edps/cli.py
git commit -m "feat: add interactive run command"
```

---

## Summary

This implementation plan covers:

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1.1-1.4 | Package scaffold and config |
| 2 | 2.1 | Init command for Azure setup |
| 3 | 3.1-3.4 | LLM client with token estimation |
| 4 | 4.1 | Confirmation UI components |
| 5 | 5.1-5.2 | Regex-based chunking |
| 6 | 6.1-6.2 | Ingest command |
| 7 | 7.1 | Prompt templates |
| 8 | 8.1 | Generate command |
| 9 | 9.1 | Template command |
| 10 | 10.1-10.2 | Interactive runner |

**Total: ~25 bite-sized tasks, each testable independently.**

---

**Next steps after Phase 10:**
- Phase 11: Claims-map synthesis (bottom-up aggregation)
- Phase 12: External metadata lookup (Gutenberg/Wikipedia)
- Phase 13: Sliding window fallback for chunking
- Phase 14: Cost tracking across sessions
- Phase 15: Validation checks (source-match)

---

*Ready for implementation.*
