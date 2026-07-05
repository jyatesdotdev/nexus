# nexus-a2a/tests — pytest suite for the A2A Weather Sub-Agent

This directory tests `../server.py`, the single module that implements the whole nexus-a2a service (an A2A-protocol weather sub-agent that the nexus-orchestrator delegates weather questions to). Hard rule for this suite: tests never touch real networks or external APIs. Every outbound HTTP call (`wttr.in`) is mocked with `respx`, and the A2A plumbing (`RequestContext`, `EventQueue`) is replaced with `unittest.mock` MagicMock/AsyncMock objects. There is no live server involved — the executor class is called directly.

## Files at this level

- `test_server.py` — the only test module. Contents:
  - `test_extract_city` — pins the city-parsing heuristic: "Weather in Tokyo" → Tokyo, trailing punctuation stripped, a bare "Paris" passes through, and trailing temporal words are dropped ("in Tokyo today" → Tokyo). If you change `extract_city`, update these expectations deliberately.
  - `test_extract_city_returns_none_without_confident_location` — pins the 2026-07-04 hardening: question-shaped messages with no "in <place>" ("What is the forecast?", "What's the weather like?") and non-place candidates leaked from multi-agent context ("in the engineering department", "in the meeting room") all return `None` — there is no "London" fallback anymore; `None` means the executor must ask for clarification.
  - `mock_context` / `mock_event_queue` fixtures — `MagicMock(spec=RequestContext)` with `task_id`/`context_id` set, and `AsyncMock(spec=EventQueue)`. Gotcha: because `mock_context.metadata` is a bare MagicMock, `server.py`'s `context.metadata.get("Authorization")` returns a MagicMock and `IdentityContext` ends up with a MagicMock `user_id` — harmless, but the "thinking" message text contains mock repr noise; assertions therefore use substring matching, not equality.
  - `test_weather_agent_success` — mocks `https://wttr.in/Berlin?format=j1` (payload includes a MATCHING `nearest_area` of Berlin/Germany, exercising the pass side of `resolved_area_matches`), runs `WeatherAgentExecutor.execute`, and asserts the exact event contract: exactly 2 `TaskStatusUpdateEvent`s enqueued — first `final=False` (thinking), second `final=True` with the formatted answer. Message text is reached via `event.status.message.parts[0].root.text` (in a2a-sdk 0.3.x, `parts` holds `Part` wrappers whose payload is `.root`).
  - `test_weather_agent_no_location_asks_for_clarification` — "What's the weather like?" (no location): still exactly 2 events (thinking + final), the final asks "Which city or place...", and `len(respx.calls) == 0` proves no wttr.in call is ever made.
  - `test_weather_agent_unrelated_resolution_asks_for_clarification` — "Weather in Fooville" with a mocked 200 payload whose `nearest_area` is Buenos Aires/Argentina: the fuzzy-geocoded weather is NEVER reported; the final message says the candidate couldn't be confidently resolved and asks for a location, with no `structured_data` metadata.
  - `test_weather_agent_api_error` — mocks a 404 from wttr.in and asserts the text "Could not retrieve weather for Atlantis. The service returned status 404." (matches `server.py`'s `httpx.HTTPStatusError` branch).
  - `test_weather_agent_parse_error` — mocks a 200 response with a malformed payload (`{"wrong_format": True}`) and asserts "Could not parse weather data for ErrorCity." (matches `server.py`'s dedicated `KeyError`/`IndexError`/`TypeError` parse-error branch; malformed payloads no longer fall through to the generic exception handler).
  - `test_weather_agent_network_error` — mocks a `httpx.RequestError` side effect and asserts the network-error message.

All 8 tests pass against the current `server.py`.

## How to run

Tests import `server` as a top-level module (pyproject's pytest config sets `pythonpath = ["."]`, so any invocation directory works):

```bash
cd <workspace-root>/nexus-a2a
uv run pytest tests/ -v
```

This mirrors how `../../nexus-stack/Makefile` (`make test`) invokes the suite (via `uv run --no-sync` against the shared workspace `.venv`). Dependencies needed: `pytest`, `pytest-asyncio` (async tests are marked explicitly with `@pytest.mark.asyncio`), `respx`, `httpx`, `a2a-sdk[http-server]==0.3.25` (1.x breaks `server.py` imports; the pyproject and requirements.txt both pin this), and the sibling `nexus-common` package (a uv workspace source) — all installed by `uv sync` at the workspace root.

## Caution

- Never replace `respx` mocks with real HTTP calls; isolation from external APIs is a workspace-wide standard.
- The "exactly 2 enqueued events" assertion is part of the service's streaming contract with the orchestrator — do not weaken it to `>= 2` to make a change pass; fix the event flow instead.
- Keep the `parts[0].root.text` access pattern; changing it to `parts[0].text` only works on other SDK versions.
