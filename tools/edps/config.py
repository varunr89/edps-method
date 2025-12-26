"""Configuration management for EDPS CLI."""
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class AzureConfig:
    """Azure AI Foundry configuration."""
    endpoint: str = ""
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"


@dataclass
class VSCodeConfig:
    """VS Code LLM Bridge configuration."""
    discovery_file: str = "~/.edps/server.json"
    timeout: int = 30  # Request timeout in seconds


@dataclass
class CouncilConfig:
    """LLM Council configuration."""
    enabled: bool = True
    tasks: list = field(default_factory=lambda: ["evaluation"])
    models: list = field(default_factory=lambda: ["gpt-5", "claude-sonnet-4.5", "gemini-3-pro"])
    chair: str = "gpt-5"
    stages: int = 3


@dataclass
class ModelsConfig:
    """Per-task model overrides."""
    chunking: str = "gpt-5"  # Not LLM-based currently
    summary: str = "gemini-3-pro"  # Large context
    podcast: str = "gpt-5"  # Placeholder
    quiz: str = "claude-sonnet-4.5"  # Quality questions
    claims_synthesis: str = "gpt-5"  # Analytical
    evaluation: str = "gpt-5"  # Used as fallback if council disabled


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
    provider: str = "vscode"  # "vscode" or "azure"
    azure: AzureConfig = field(default_factory=AzureConfig)
    vscode: VSCodeConfig = field(default_factory=VSCodeConfig)
    council: CouncilConfig = field(default_factory=CouncilConfig)
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

        # Load provider
        if "provider" in data:
            config.provider = data["provider"]

        # Load azure config
        if "azure" in data:
            azure_data = data["azure"]
            config.azure = AzureConfig(
                endpoint=azure_data.get("endpoint", ""),
                api_key=_resolve_env_var(azure_data.get("api_key", "")),
                model=azure_data.get("model", "claude-sonnet-4-20250514"),
            )

        # Load vscode config
        if "vscode" in data:
            vscode_data = data["vscode"]
            config.vscode = VSCodeConfig(
                discovery_file=vscode_data.get("discovery_file", config.vscode.discovery_file),
                timeout=vscode_data.get("timeout", config.vscode.timeout),
            )

        # Load council config
        if "council" in data:
            council_data = data["council"]
            config.council = CouncilConfig(
                enabled=council_data.get("enabled", config.council.enabled),
                tasks=council_data.get("tasks", config.council.tasks),
                models=council_data.get("models", config.council.models),
                chair=council_data.get("chair", config.council.chair),
                stages=council_data.get("stages", config.council.stages),
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
                evaluation=models_data.get("evaluation", config.models.evaluation),
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
        "provider": config.provider,
        "azure": asdict(config.azure),
        "vscode": asdict(config.vscode),
        "council": asdict(config.council),
        "models": asdict(config.models),
        "defaults": asdict(config.defaults),
    }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def _resolve_env_var(value: str) -> str:
    """Resolve ${ENV_VAR} syntax in config values."""
    if value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.environ.get(env_var, "")
    return value
