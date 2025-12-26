"""Tests for VS Code LLM Bridge client."""
import json
import pytest
import requests
from unittest.mock import patch, MagicMock

from edps.core.vscode_client import VSCodeClient, VSCodeUnavailableError


class TestVSCodeClient:
    def test_reads_discovery_file(self, tmp_path):
        discovery_file = tmp_path / "server.json"
        discovery_file.write_text(json.dumps({
            "port": 52341,
            "pid": 12345,
            "started": "2025-12-25T10:00:00Z",
            "models": ["gpt-5"]
        }))

        client = VSCodeClient(str(discovery_file))
        info = client._read_discovery_file()

        assert info["port"] == 52341
        assert "gpt-5" in info["models"]

    def test_raises_when_discovery_file_missing(self, tmp_path):
        discovery_file = tmp_path / "nonexistent.json"
        client = VSCodeClient(str(discovery_file))

        with pytest.raises(VSCodeUnavailableError):
            client._read_discovery_file()

    @patch('edps.core.vscode_client.requests.post')
    def test_complete_calls_server(self, mock_post, tmp_path):
        discovery_file = tmp_path / "server.json"
        discovery_file.write_text(json.dumps({
            "port": 52341,
            "pid": 12345,
            "started": "2025-12-25T10:00:00Z",
            "models": ["gpt-5"]
        }))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Hello!",
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }
        mock_post.return_value = mock_response

        client = VSCodeClient(str(discovery_file))
        result = client.complete("Say hello", model="gpt-5")

        assert result["content"] == "Hello!"
        mock_post.assert_called_once()

    @patch('edps.core.vscode_client.requests.get')
    def test_health_check_returns_true_on_success(self, mock_get, tmp_path):
        discovery_file = tmp_path / "server.json"
        discovery_file.write_text(json.dumps({"port": 52341, "pid": 1, "started": "", "models": []}))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = VSCodeClient(str(discovery_file))
        assert client.health_check() is True

    @patch('edps.core.vscode_client.requests.get')
    def test_health_check_returns_false_on_failure(self, mock_get, tmp_path):
        discovery_file = tmp_path / "server.json"
        discovery_file.write_text(json.dumps({"port": 52341, "pid": 1, "started": "", "models": []}))

        mock_get.side_effect = requests.RequestException("Connection failed")

        client = VSCodeClient(str(discovery_file))
        assert client.health_check() is False

    def test_health_check_returns_false_when_no_discovery_file(self, tmp_path):
        discovery_file = tmp_path / "nonexistent.json"
        client = VSCodeClient(str(discovery_file))
        assert client.health_check() is False
