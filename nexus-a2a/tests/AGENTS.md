# nexus-a2a/tests — pytest suite for the A2A Weather Sub-Agent

This directory tests `../server.py`, the single module that implements the whole nexus-a2a service (an A2A-protocol weather sub-agent that the nexus-orchestrator delegates weather questions to). Hard rule for this suite: tests never touch real networks or external APIs. Every outbound HTTP call (`wttr.in`) is mocked with `respx`, and the A2A plumbing (`RequestContext`, `EventQueue`) is replaced with `unittest.mock` MagicMock/AsyncMock objects. There is no live server involved — the executor class is called directly.

## Files at this level

- `test_server.py` — the only test module. Contents:
  - `test_extract_city` — pins the city-parsing heuristic: "Weather in Tokyo" → Tokyo, trailing punctuation stripped, a bare "Paris" passes through, and question-shaped messages with no "in <city>" default to "London". If you change `extract_city`, update these expectations deliberately.
  - `mock_context` / `mock_event_queue` fixtures — `MagicMock(spec=RequestContext)` with `task_id`/`context_id` set, and `AsyncMock(spec=EventQueue)`. Gotcha: because `mock_context.metadata` is a bare MagicMock, `server.py`'s `context.metadata.get("Authorization")` returns a MagicMock and `IdentityContext` ends up with a MagicMock `user_id` — harmless, but the "thinking" message text contains mock repr noise; assertions therefore use substring matching, not equality.
  - `test_weather_agent_success` — mocks `https://wttr.in/Berlin?format=j1`, runs `WeatherAgentExecutor.execute`, and asserts the exact event contract: exactly 2 `TaskStatusUpdateEvent`s enqueued — first `final=False` (thinking), second `final=True` with the formatted answer. Message text is reached via `event.status.message.parts[0].root.text` (in a2a-sdk 0.3.x, `parts` holds `Part` wrappers whose payload is `.root`).
  - `test_weather_agent_api_error` — CURRENTLY FAILING. Asserts the text "Could not retrieve weather for Atlantis. The service returned status 404." but `server.py` produces "...Service returned status 404." (no "The"). One side must be aligned.
  - `test_weather_agent_parse_error` — CURRENTLY FAILING. Asserts "Could not parse weather data for ErrorCity.", but `server.py` has no parse-error branch: a malformed wttr.in payload raises `KeyError`, caught by the generic handler, yielding "An unexpected error occurred: 'current_condition'". Either add a parse-error branch (e.g. catch `KeyError`/`IndexError`) to `server.py` or rewrite the assertion.
  - `test_weather_agent_network_error` — mocks a `httpx.RequestError` side effect and asserts the network-error message. Passes.

So the suite is 3 passed / 2 failed against the current `server.py`; the two failures are stale expectations (or an unfinished server change), not flaky tests.

## How to run

Tests import `server` as a top-level module, so run from the repo root with the root on `PYTHONPATH`:

```bash
cd /Users/jyates/Repositories/nexus/nexus-a2a
PYTHONPATH=. venv/bin/python -m pytest tests/ -v
```

This mirrors how `../../nexus-stack/Makefile` (`make test`) invokes the suite (it uses the nexus-orchestrator venv's Python). Dependencies needed: `pytest`, `pytest-asyncio` (async tests are marked explicitly with `@pytest.mark.asyncio`; no asyncio-mode config file exists), `respx`, `httpx`, `a2a-sdk==0.3.25` (1.x breaks `server.py` imports), and the sibling `nexus-common` package (`pip install -e ../nexus-common`) — all pulled in by `pip install -r ../requirements.txt` run from the repo root, except that the a2a-sdk pin may need to be applied manually.

## Caution

- Never replace `respx` mocks with real HTTP calls; isolation from external APIs is a workspace-wide standard.
- The "exactly 2 enqueued events" assertion is part of the service's streaming contract with the orchestrator — do not weaken it to `>= 2` to make a change pass; fix the event flow instead.
- Keep the `parts[0].root.text` access pattern; changing it to `parts[0].text` only works on other SDK versions.
