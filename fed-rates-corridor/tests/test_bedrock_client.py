"""Unit tests for the Bedrock client module."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.components.bedrock_client import generate_bedrock_summary, invoke_bedrock


class TestInvokeBedrock:
    """Tests for invoke_bedrock."""

    @patch("app.components.bedrock_client._get_bedrock_client")
    def test_successful_invocation(self, mock_get_client):
        """Test successful Bedrock API call."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_body = json.dumps({"content": [{"text": "Generated summary text"}]}).encode()
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=response_body))
        }

        result = invoke_bedrock("Test prompt")
        assert result == "Generated summary text"

    @patch("app.components.bedrock_client._get_bedrock_client")
    def test_returns_empty_on_no_client(self, mock_get_client):
        """Test graceful fallback when client is None."""
        mock_get_client.return_value = None
        result = invoke_bedrock("Test prompt")
        assert result == ""

    @patch("app.components.bedrock_client._get_bedrock_client")
    def test_handles_api_error(self, mock_get_client):
        """Test graceful handling of API errors."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.invoke_model.side_effect = Exception("API Error")

        result = invoke_bedrock("Test prompt")
        assert result == ""

    @patch("app.components.bedrock_client._get_bedrock_client")
    def test_uses_correct_model_id(self, mock_get_client):
        """Test that the correct model ID is used."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_body = json.dumps({"content": [{"text": "ok"}]}).encode()
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=response_body))
        }

        with patch.dict(os.environ, {"BEDROCK_MODEL_ID": "test-model"}):
            invoke_bedrock("prompt")

        call_kwargs = mock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "test-model"


class TestGenerateBedrockSummary:
    """Tests for generate_bedrock_summary."""

    @patch("app.components.bedrock_client.invoke_bedrock")
    def test_economist_persona(self, mock_invoke):
        """Test economist persona prompt construction."""
        mock_invoke.return_value = "Technical analysis..."
        result = generate_bedrock_summary("rate data here", "economist")
        assert result == "Technical analysis..."

        prompt = mock_invoke.call_args[0][0]
        assert "monetary economist" in prompt
        assert "rate data here" in prompt

    @patch("app.components.bedrock_client.invoke_bedrock")
    def test_executive_persona(self, mock_invoke):
        """Test executive persona prompt construction."""
        mock_invoke.return_value = "Executive brief..."
        result = generate_bedrock_summary("data", "executive")
        assert result == "Executive brief..."

        prompt = mock_invoke.call_args[0][0]
        assert "senior Federal Reserve executive" in prompt

    @patch("app.components.bedrock_client.invoke_bedrock")
    def test_public_persona(self, mock_invoke):
        """Test public persona prompt construction."""
        mock_invoke.return_value = "Simple explanation..."
        result = generate_bedrock_summary("data", "public")
        assert result == "Simple explanation..."

        prompt = mock_invoke.call_args[0][0]
        assert "no economics background" in prompt

    @patch("app.components.bedrock_client.invoke_bedrock")
    def test_fallback_on_empty_response(self, mock_invoke):
        """Test that empty string is returned on failure."""
        mock_invoke.return_value = ""
        result = generate_bedrock_summary("data", "economist")
        assert result == ""
