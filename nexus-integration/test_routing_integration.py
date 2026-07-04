import asyncio
import json
import os
import uuid

import httpx
import pytest

# ==========================================
# CONCEPT: End-to-End Routing Verification
# EDUCATIONAL NOTE: The other integration tests in this directory check that individual
# containers are *reachable* (A2A discovery, Redis, Postgres). This test goes one level
# deeper: it drives the orchestrator's real user-facing endpoint (`POST /run_sse`) with a
# natural-language prompt and verifies that the root agent actually DELEGATED the request
# to the correct specialized sub-agent. This exercises the full chain:
# HTTP -> identity middleware -> ADK root agent -> LLM routing decision -> sub-agent
# (A2A or MCP) -> streamed SSE answer. It is the closest thing to "a user typed a message
# in the chat UI" that can be asserted without a browser.
# ==========================================

# CONFIGURATION: Same env-var override pattern as the sibling tests.
# The orchestrator publishes host port 8080 (nexus-stack/docker-compose.yml), so the
# default works both from the host and from inside a container on nexus-net when
# ORCHESTRATOR_URL is set (e.g. ORCHESTRATOR_URL=http://orchestrator:8080).
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8080").rstrip("/")

# MOCK IDENTITY: The orchestrator's middleware (orchestrator/middleware.py) rejects
# /run_sse requests whose `user_id` is not a structurally valid Nexus mock JWT.
# EDUCATIONAL NOTE: This is the exact token the React UI sends (nexus-ui/src/App.tsx);
# using the same one keeps this test faithful to the real client contract.
MOCK_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".mock_user_123"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)

# APP NAME: SimpleAgentLoader in orchestrator/server.py accepts 'containerized_agents'.
APP_NAME = "containerized_agents"

# TIMEOUTS: A routed turn involves at least two LLM calls (root agent decision +
# sub-agent answer) plus a live sub-agent round-trip, so it needs a generous but HARD
# ceiling — a hung stream must fail the test rather than hang the suite.
STREAM_TIMEOUT_SECONDS = 120
HEALTH_TIMEOUT_SECONDS = 3


async def _skip_unless_orchestrator_up() -> None:
    """Skip (not fail) the calling test when the stack is not running.

    EDUCATIONAL NOTE: Integration tests must be safe to invoke on a stackless
    machine (e.g. a laptop or CI runner without Docker up). Reachability of the
    orchestrator is a *precondition*, not the property under test, so we probe
    the standardized nexus_common `/health` endpoint and translate "connection
    refused" into pytest.skip instead of a red failure.
    """
    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_SECONDS) as client:
            resp = await client.get(f"{ORCHESTRATOR_URL}/health")
            if resp.status_code != 200:
                pytest.skip(
                    f"Orchestrator /health returned {resp.status_code} at "
                    f"{ORCHESTRATOR_URL} — stack not healthy; skipping routing test."
                )
    except httpx.HTTPError as e:
        pytest.skip(
            f"Orchestrator unreachable at {ORCHESTRATOR_URL} ({e.__class__.__name__}). "
            "Start the stack with 'make up' in ../nexus-stack to run this test."
        )


async def _run_prompt(prompt: str) -> tuple[str, set[str]]:
    """POST a prompt to /run_sse and consume the SSE stream to completion.

    Returns (final_answer_text, agents_seen) where agents_seen is the union of
    every event's `author` and every `transferToAgent` delegation target.

    EDUCATIONAL NOTE: Delegation IS reliably detectable from the /run_sse stream:
    each ADK event carries an `author` field (the emitting agent's name), and the
    root agent's hand-off appears as `actions.transferToAgent` — the React UI's
    "Delegating to ..." banner is driven by exactly these fields, so this test
    asserts routing the same way the real client observes it.
    """
    payload = {
        "app_name": APP_NAME,
        "user_id": MOCK_JWT,
        # Fresh session per call; the middleware auto-creates unknown sessions.
        "session_id": f"routing-test-{uuid.uuid4().hex}",
        # streaming=False still yields an SSE stream (one `data:` line per ADK
        # event) but without token-level partial deltas, which keeps the final
        # answer easy to reassemble.
        "streaming": False,
        "new_message": {"role": "user", "parts": [{"text": prompt}]},
    }

    agents_seen: set[str] = set()
    final_text_chunks: list[str] = []

    # HARD TIMEOUT: asyncio.timeout bounds the *entire* stream consumption, so a
    # stalled LLM or wedged sub-agent cannot hang the suite indefinitely.
    async with asyncio.timeout(STREAM_TIMEOUT_SECONDS):
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, read=STREAM_TIMEOUT_SECONDS)
        ) as client:
            async with client.stream(
                "POST", f"{ORCHESTRATOR_URL}/run_sse", json=payload
            ) as response:
                assert response.status_code == 200, (
                    f"/run_sse returned {response.status_code}: "
                    f"{await response.aread()!r}"
                )
                # SSE PARSING: Each event arrives as a 'data: {json}' line,
                # mirroring the parser in nexus-ui/src/App.tsx.
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        event = json.loads(line[len("data: ") :])
                    except json.JSONDecodeError:
                        continue

                    author = event.get("author")
                    if author:
                        agents_seen.add(author)

                    # ADK serializes camelCase, but accept snake_case defensively
                    # (the UI does the same for tool confirmations).
                    actions = event.get("actions") or {}
                    transfer = actions.get("transferToAgent") or actions.get(
                        "transfer_to_agent"
                    )
                    if transfer:
                        agents_seen.add(transfer)

                    # FINAL ANSWER: with streaming=False every content-bearing
                    # event is authoritative (no partial deltas to accumulate).
                    if event.get("partial") is not True:
                        content = event.get("content") or {}
                        for part in content.get("parts") or []:
                            text = part.get("text")
                            if text:
                                final_text_chunks.append(text)

    return "".join(final_text_chunks), agents_seen


# EDUCATIONAL NOTE: The prompts and expected agent names below come straight from the
# orchestrator's own routing baseline (orchestrator/eval_cases.py), so this test and the
# LLM evals agree on what "correct routing" means. The names 'weather_sub_agent' and
# 'mcp_agent' are assigned in orchestrator/agents/dynamic_agents.py when exactly one
# A2A/MCP URL is configured — the default in nexus-stack/docker-compose.yml.
@pytest.mark.asyncio
async def test_weather_prompt_routes_to_a2a_agent():
    """A weather question must be delegated to the A2A weather sub-agent."""
    await _skip_unless_orchestrator_up()

    answer, agents_seen = await _run_prompt("What is the weather like in Paris today?")

    assert answer.strip(), "Expected a non-empty final answer from the orchestrator."
    assert "weather_sub_agent" in agents_seen, (
        "Expected delegation to 'weather_sub_agent' (A2A protocol), but the stream "
        f"only showed these agents: {sorted(agents_seen)}. Answer was: {answer!r}"
    )


@pytest.mark.asyncio
async def test_hr_prompt_routes_to_mcp_agent():
    """An HR-directory question must be delegated to the MCP HR sub-agent."""
    await _skip_unless_orchestrator_up()

    answer, agents_seen = await _run_prompt("Who works in the engineering department?")

    assert answer.strip(), "Expected a non-empty final answer from the orchestrator."
    assert "mcp_agent" in agents_seen, (
        "Expected delegation to 'mcp_agent' (MCP protocol), but the stream only "
        f"showed these agents: {sorted(agents_seen)}. Answer was: {answer!r}"
    )


# MAIN BLOCK: Mirrors the sibling tests — allows 'python test_routing_integration.py'.
if __name__ == "__main__":
    asyncio.run(test_weather_prompt_routes_to_a2a_agent())
    asyncio.run(test_hr_prompt_routes_to_mcp_agent())
