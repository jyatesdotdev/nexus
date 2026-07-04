# orchestrator/adapters/ — foundation model adapters

This package holds custom LLM backends for the Nexus orchestrator. The orchestrator is built on Google ADK and defaults to Gemini, but ADK lets any model be plugged in by implementing `google.adk.models.base_llm.BaseLlm` and registering the class with `google.adk.models.registry.LLMRegistry`. The registry matches the `AGENT_MODEL` string (set via env var, see `orchestrator/config.py`) against each adapter's `supported_models()` regex patterns.

KNOWN GAP: `orchestrator/app.py` does `from . import adapters` with the comment "Register foundation model adapters", but `__init__.py` here is EMPTY, so neither adapter module is actually imported at app startup and `LLMRegistry.register(...)` never runs in production. The Ollama adapter currently only gets registered when something imports `orchestrator.adapters.ollama_adapter` directly (the test suite does). If `AGENT_MODEL=ollama/...` fails with an unknown-model error, this is why; the fix is to import the adapter modules inside `__init__.py`.

## Files

- `__init__.py` — Empty (see the gap above; it is supposed to import the adapter modules so their module-level `LLMRegistry.register` calls execute).
- `ollama_adapter.py` — `OllamaAdapter(BaseLlm)`. Handles any model string matching `ollama/.*` (e.g. `AGENT_MODEL=ollama/llama3`); strips the `ollama/` prefix before calling the local Ollama HTTP API. Server URL comes from `OLLAMA_BASE_URL` (default `http://localhost:11434`; use `http://host.docker.internal:11434` from inside Docker on macOS). Converts ADK `LlmRequest` (system instruction + contents, mapping role `model` -> `assistant`) into Ollama `/api/chat` messages; supports both non-streaming and line-delimited-JSON streaming (`partial` flag set from Ollama's `done` field). Text-only: tool/function calls and non-text parts are dropped. Calls `LLMRegistry.register(OllamaAdapter)` at module import time.
- `bedrock_adapter.py` — `BedrockAdapter(BaseLlm)`. Deliberately skeletal/educational: matches `anthropic\.claude-.*` model strings but `generate_content_async` just yields a hardcoded canned response; it makes no AWS calls and is NOT registered with `LLMRegistry` anywhere. Do not expect Bedrock to work.

## How to test

```bash
cd /Users/jyates/Repositories/nexus/nexus-orchestrator
./venv/bin/python -m pytest tests/test_ollama_adapter.py
```

Tests mock `httpx.AsyncClient`; no Ollama server is needed. To try the adapter for real: run `ollama serve` with a pulled model, set `AGENT_MODEL=ollama/llama3` (and register the adapter — see the gap above), then `./venv/bin/python main.py chat "hi"`.

## Caution

- New adapters must subclass `BaseLlm`, implement `supported_models()` (regex list) and `generate_content_async` (async generator of `LlmResponse`), and be registered with `LLMRegistry` AND actually imported at startup.
- Do not change the `ollama/` prefix convention without updating README examples and any `.env`/compose files in nexus-stack.
