import sys
import os

# Add root directory to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from orchestrator.adapters.ollama_adapter import OllamaAdapter


@pytest.mark.asyncio
async def test_ollama_adapter_generate_non_streaming() -> None:
    adapter = OllamaAdapter(model="ollama/llama3")

    # Mock response from Ollama
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "Hello from local model!"},
        "done": True,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        request = LlmRequest(
            contents=[types.Content(role="user", parts=[types.Part(text="Hi")])]
        )

        responses = []
        async for resp in adapter.generate_content_async(request, stream=False):
            responses.append(resp)

        assert len(responses) == 1
        assert responses[0].content is not None
        assert responses[0].content.parts is not None
        assert responses[0].content.parts[0].text == "Hello from local model!"
        assert not responses[0].partial

        # Verify the call to Ollama API
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["model"] == "llama3"
        assert kwargs["json"]["messages"][0]["content"] == "Hi"


@pytest.mark.asyncio
async def test_ollama_adapter_generate_streaming() -> None:
    adapter = OllamaAdapter(model="ollama/llama3")

    # Mock stream chunks
    chunks = [
        '{"message": {"content": "Hello"}, "done": false}',
        '{"message": {"content": " world"}, "done": true}',
    ]

    async def mock_aiter_lines() -> Any:
        for chunk in chunks:
            yield chunk

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines
    mock_response.raise_for_status = MagicMock()

    # Mock the context manager for client.stream
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)
    # mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    # mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        request = LlmRequest(
            contents=[types.Content(role="user", parts=[types.Part(text="Hi")])]
        )

        responses = []
        async for resp in adapter.generate_content_async(request, stream=True):
            responses.append(resp)

        assert len(responses) == 2
        assert responses[0].content is not None
        assert responses[0].content.parts is not None
        assert responses[0].content.parts[0].text == "Hello"
        assert responses[0].partial
        assert responses[1].content is not None
        assert responses[1].content.parts is not None
        assert responses[1].content.parts[0].text == " world"
        assert not responses[1].partial
