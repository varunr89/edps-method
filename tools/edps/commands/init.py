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
