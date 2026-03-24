# JSON: A standard data format for structured data, widely used in APIs.
# EDUCATIONAL NOTE: [Why] json.loads() converts a JSON string (from a network response)
# into a Python dictionary that we can easily work with.
import json
import os

# HTTPX: A next-generation HTTP client for Python.
# EDUCATIONAL NOTE: [Why] It fully supports asynchronous requests, which is essential for
# a high-performance AI orchestrator.
import httpx
from typing import AsyncGenerator, List, Any, Dict
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

# REGISTRY PATTERN: LLMRegistry is a central place to "register" new model adapters.
# EDUCATIONAL NOTE: [Why] It allows the ADK to discover and use new adapters dynamically without
# hardcoding them into the core logic.
from google.adk.models.registry import LLMRegistry
from google.genai import types


class OllamaAdapter(BaseLlm):
    """
    CONCEPT: Local Foundation Model Support via Ollama
    """

    model: str = "llama3"  # Default local model
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @classmethod
    def supported_models(cls) -> List[str]:
        # REGULAR EXPRESSIONS: r"ollama/.*" is a pattern.
        # EDUCATIONAL NOTE: [Why] This tells the ADK that any model string starting with 'ollama/'
        # should be handled by this adapter.
        return [r"ollama/.*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # STRING MANIPULATION: Stripping the 'ollama/' prefix.
        # EDUCATIONAL NOTE: [Why] The ADK uses 'ollama/llama3' to identify this adapter, but
        # the local Ollama API just expects 'llama3'.
        actual_model = self.model.replace("ollama/", "")

        # LIST COMPREHENSION: A concise way to transform lists in Python.
        # (See the text construction below)
        messages: List[Dict[str, Any]] = []

        if llm_request.config and llm_request.config.system_instruction:
            messages.append(
                {"role": "system", "content": llm_request.config.system_instruction}
            )

        for content in llm_request.contents:
            role = "assistant" if content.role == "model" else (content.role or "user")
            # JOIN: Combines a list of strings into a single string.
            parts = content.parts or []
            text = "".join([p.text for p in parts if p.text])
            messages.append({"role": role, "content": text})

        payload = {"model": actual_model, "messages": messages, "stream": stream}

        # ASYNC CONTEXT MANAGER: Ensures the HTTP connection pool is closed correctly.
        async with httpx.AsyncClient(timeout=60.0) as client:
            if not stream:
                # POST REQUEST: Sending data to an API endpoint.
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                # ERROR HANDLING: Automatically raises an exception if the status code is 4xx or 5xx.
                response.raise_for_status()
                data = response.json()

                yield LlmResponse(
                    partial=False,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=data["message"]["content"])],
                    ),
                )
            else:
                # STREAMING REQUEST: Processing the response line-by-line as it arrives.
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    # AITER_LINES: An asynchronous iterator for response lines.
                    # EDUCATIONAL NOTE: [Why] Ollama streams responses as a series of JSON objects, one per line.
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield LlmResponse(
                                # PARTIAL FLAG: Tells the ADK if this is just a chunk or the final result.
                                partial=not chunk.get("done", False),
                                content=types.Content(
                                    role="model",
                                    parts=[
                                        types.Part(text=chunk["message"]["content"])
                                    ],
                                ),
                            )


# AUTOMATIC REGISTRATION: This module-level code runs exactly once when
# the module is first imported.
# EDUCATIONAL NOTE: [Why] This "registers" the adapter so the rest of the app can use it immediately.
LLMRegistry.register(OllamaAdapter)
