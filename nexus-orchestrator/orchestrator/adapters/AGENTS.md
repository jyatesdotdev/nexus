# orchestrator/adapters/ — foundation model adapters

This package holds custom LLM backends for the Nexus orchestrator. The orchestrator is built on Google ADK and defaults to Gemini, but ADK lets any model be plugged in by implementing `google.adk.models.base_llm.BaseLlm` and registering the class with `google.adk.models.registry.LLMRegistry`. The registry matches the `AGENT_MODEL` string (set via env var, see `orchestrator/config.py`) against each adapter's `supported_models()` regex patterns.

Registration wiring: `orchestrator/app.py` does `from . import adapters`, and `__init__.py` here imports both adapter modules so their module-level `LLMRegistry.register(...)` calls execute at app startup. If you add a new adapter module, you MUST also import it from `__init__.py`, or `AGENT_MODEL=<your-prefix>/...` will fail with an unknown-model error in production.

## Files

- `__init__.py` — Imports `ollama_adapter` and `bedrock_adapter` so registration side effects run (the bedrock stub registers nothing and needs no boto3 at import time, so importing it is harmless).
- `ollama_adapter.py` — `OllamaAdapter(BaseLlm)`. Handles any model string matching `ollama/.*` (e.g. `AGENT_MODEL=ollama/llama3`); strips the `ollama/` prefix before calling the local Ollama HTTP API. Server URL comes from `OLLAMA_BASE_URL` (default `http://localhost:11434`; use `http://host.docker.internal:11434` from inside Docker on macOS). Converts ADK `LlmRequest` (system instruction + contents, mapping role `model` -> `assistant`) into Ollama `/api/chat` messages; supports both non-streaming and line-delimited-JSON streaming (`partial` flag set from Ollama's `done` field). Text-only: tool/function calls and non-text parts are dropped. Calls `LLMRegistry.register(OllamaAdapter)` at module import time.
- `bedrock_adapter.py` — `BedrockAdapter(BaseLlm)`. Deliberately skeletal/educational: matches `anthropic\.claude-.*` model strings but `generate_content_async` just yields a hardcoded canned response; it makes no AWS calls and is NOT registered with `LLMRegistry` anywhere. Do not expect Bedrock to work.

## How to test

```bash
cd /Users/jyates/Repositories/nexus/nexus-orchestrator
uv run pytest tests/test_ollama_adapter.py
```

Tests mock `httpx.AsyncClient`; no Ollama server is needed. To try the adapter for real: run `ollama serve` with a pulled model, set `AGENT_MODEL=ollama/llama3`, then `uv run python main.py chat "hi"`.

## Caution

- New adapters must subclass `BaseLlm`, implement `supported_models()` (regex list) and `generate_content_async` (async generator of `LlmResponse`), and be registered with `LLMRegistry` AND actually imported at startup.
- Do not change the `ollama/` prefix convention without updating README examples and any `.env`/compose files in nexus-stack.
