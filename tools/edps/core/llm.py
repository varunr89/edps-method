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
