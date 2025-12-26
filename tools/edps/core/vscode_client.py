"""VS Code LLM Bridge client."""
import json
from pathlib import Path
from typing import Optional

import requests


class VSCodeUnavailableError(Exception):
    """Raised when VS Code bridge is not available."""
    pass


class VSCodeClient:
    """Client for VS Code LLM Bridge."""

    def __init__(self, discovery_file: str = "~/.edps/server.json", timeout: int = 30):
        self.discovery_file = Path(discovery_file).expanduser()
        self.timeout = timeout
        self._cached_info: Optional[dict] = None

    def _read_discovery_file(self) -> dict:
        """Read server info from discovery file."""
        if not self.discovery_file.exists():
            raise VSCodeUnavailableError(
                f"Discovery file not found: {self.discovery_file}\n"
                "Make sure VS Code is running with the EDPS LLM Bridge extension."
            )

        try:
            content = self.discovery_file.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            raise VSCodeUnavailableError(f"Failed to read discovery file: {e}")

    def _get_base_url(self) -> str:
        """Get server base URL."""
        info = self._read_discovery_file()
        return f"http://localhost:{info['port']}"

    def health_check(self) -> bool:
        """Check if server is responding."""
        try:
            url = f"{self._get_base_url()}/health"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except (requests.RequestException, VSCodeUnavailableError):
            return False

    def get_models(self) -> list[str]:
        """Get available models from server."""
        url = f"{self._get_base_url()}/models"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("models", [])

    def complete(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> dict:
        """Send completion request to VS Code bridge.

        Returns:
            dict with 'content' and 'usage' keys
        """
        url = f"{self._get_base_url()}/complete"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            raise VSCodeUnavailableError(f"Request timed out after {self.timeout}s")
        except requests.ConnectionError:
            raise VSCodeUnavailableError("Cannot connect to VS Code bridge")
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                raise VSCodeUnavailableError("Rate limited by VS Code")
            raise
