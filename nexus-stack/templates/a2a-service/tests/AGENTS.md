# nexus-__SERVICE_NAME__/tests — pytest suite for the __SERVICE_TITLE__ Sub-Agent

Tests `../server.py`. Hard rule: tests never touch real networks — every outbound HTTP call is mocked with `respx`, and the A2A plumbing (`RequestContext`, `EventQueue`) is replaced with `MagicMock(spec=RequestContext)` / `AsyncMock(spec=EventQueue)`. The executor class is called directly; no live server.

## Files at this level

- `test_server.py` —
  - `test_process_query` — pins the domain function's default (scaffold) behavior, including the `"For context:"` stripping. When you implement your real capability, update these expectations deliberately.
  - `test_execute_two_phase_contract` — asserts the streaming contract: exactly 2 `TaskStatusUpdateEvent`s enqueued, first `final=False` (thinking), second `final=True` with the answer. Message text is reached via `event.status.message.parts[0].root.text` (a2a-sdk 0.3.x wraps parts; the payload is `.root`). Do not weaken the `== 2` assertion — it is part of the contract with the orchestrator.
  - `test_execute_with_external_api` / `..._http_error` / `..._network_error` — the respx mocking pattern for the `EXTERNAL_API_URL` boundary (success, HTTP-status error, network error), mirroring nexus-a2a's suite.

## How to run

```bash
cd nexus-__SERVICE_NAME__
uv run pytest tests/ -v
```

Gotcha: `mock_context.metadata` is a bare MagicMock, so `IdentityContext` ends up with a MagicMock `user_id`; the "thinking" text therefore contains mock repr noise, and assertions use substring matching, not equality.
