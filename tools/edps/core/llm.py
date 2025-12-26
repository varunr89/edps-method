"""LLM client with provider routing."""
from dataclasses import dataclass
from typing import Optional

from edps.config import EdpsConfig
from edps.core.tokens import estimate_tokens, estimate_cost
from edps.core.vscode_client import VSCodeClient, VSCodeUnavailableError


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str
    provider: str = "azure"


@dataclass
class LLMPreview:
    """Preview of what an LLM call will do."""
    prompt: str
    input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float
    model: str


class LLMClient:
    """Client with VS Code primary, Azure fallback."""

    def __init__(self, config: EdpsConfig):
        self.config = config
        self.provider = config.provider
        self.temperature = config.defaults.temperature
        self.max_tokens = config.defaults.max_tokens

        # Initialize VS Code client if primary
        self._vscode_client: Optional[VSCodeClient] = None
        if self.provider == "vscode":
            self._vscode_client = VSCodeClient(
                discovery_file=config.vscode.discovery_file,
                timeout=config.vscode.timeout,
            )

        # Azure client (lazy loaded)
        self._azure_client = None
        self.azure_config = config.azure

    @property
    def default_model(self) -> str:
        if self.provider == "vscode":
            return "gpt-5"  # Default for VS Code
        return self.azure_config.model

    def _get_azure_client(self):
        """Lazy-load the Anthropic Foundry client."""
        if self._azure_client is None:
            from anthropic import AnthropicFoundry
            self._azure_client = AnthropicFoundry(
                api_key=self.azure_config.api_key,
                base_url=self.azure_config.endpoint,
            )
        return self._azure_client

    def preview(
        self,
        prompt: str,
        model: Optional[str] = None,
        estimated_output_tokens: int = 1000,
    ) -> LLMPreview:
        """Preview an LLM call without executing."""
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
        """Execute an LLM completion with provider routing."""
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens

        # Try VS Code first if configured
        if self.provider == "vscode" and self._vscode_client:
            try:
                return self._complete_vscode(prompt, model, temperature, max_tokens)
            except VSCodeUnavailableError as e:
                # Fall back to Azure if available
                if self.azure_config.api_key:
                    print(f"[Warning] VS Code bridge unavailable: {e}")
                    print("[Fallback] Using Azure")
                    return self._complete_azure(prompt, model, temperature, max_tokens)
                raise

        return self._complete_azure(prompt, model, temperature, max_tokens)

    def _complete_vscode(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Complete via VS Code bridge."""
        result = self._vscode_client.complete(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return LLMResponse(
            content=result["content"],
            input_tokens=result["usage"]["input_tokens"],
            output_tokens=result["usage"]["output_tokens"],
            cost=0.0,  # VS Code/Copilot is included in subscription
            model=model,
            provider="vscode",
        )

    def _complete_azure(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Complete via Azure AI Foundry."""
        client = self._get_azure_client()

        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = estimate_cost(input_tokens, output_tokens, model)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model=model,
            provider="azure",
        )
