# EDUCATIONAL NOTE: Testing the Reviewer Enforcement Wiring
# [Why] tests/test_reviewer_enforcement.py proves ReviewerEnforcementRunner
# behaves correctly; THESE tests prove it is actually wired into both
# execution paths — the CLI/evals path (app.get_runner) and the HTTP path
# (server.GovernedAdkWebServer) — and that the REVIEWER_ENFORCEMENT config
# flag can switch it off. They also pin the private ADK seam we override
# (_create_runner): if an ADK upgrade removes it, these tests fail loudly.
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from google.adk.agents.llm_agent import LlmAgent as Agent

from orchestrator import config
from orchestrator.reviewer import (
    LoopDetectionRunner,
    ReviewerEnforcementRunner,
    build_governed_runner,
)
from orchestrator.server import GovernedAdkWebServer
from google.adk.cli.adk_web_server import AdkWebServer


def _make_agent_with_reviewer() -> Agent:
    reviewer = Agent(name="reviewer_agent", description="QA critic.")
    return Agent(
        name="root_agent",
        description="router",
        sub_agents=[reviewer],
    )


def test_build_governed_runner_full_pipeline() -> None:
    raw_runner = MagicMock()
    agent = _make_agent_with_reviewer()

    governed = build_governed_runner(raw_runner, agent, enforce_review=True)

    # Outermost: reviewer enforcement; inside it: loop detection; then the raw runner.
    assert isinstance(governed, ReviewerEnforcementRunner)
    assert isinstance(governed._runner, LoopDetectionRunner)
    assert governed._runner._runner is raw_runner


def test_build_governed_runner_respects_toggle_off() -> None:
    raw_runner = MagicMock()
    agent = _make_agent_with_reviewer()

    governed = build_governed_runner(raw_runner, agent, enforce_review=False)

    assert isinstance(governed, LoopDetectionRunner)
    assert not isinstance(governed, ReviewerEnforcementRunner)


def test_build_governed_runner_without_reviewer_agent() -> None:
    raw_runner = MagicMock()
    agent = Agent(name="root_agent", description="router")  # no sub-agents

    governed = build_governed_runner(raw_runner, agent, enforce_review=True)

    assert isinstance(governed, LoopDetectionRunner)
    assert not isinstance(governed, ReviewerEnforcementRunner)


def _make_web_server() -> GovernedAdkWebServer:
    return GovernedAdkWebServer(
        agent_loader=MagicMock(),
        session_service=MagicMock(),
        memory_service=MagicMock(),
        artifact_service=MagicMock(),
        credential_service=MagicMock(),
        eval_sets_manager=MagicMock(),
        eval_set_results_manager=MagicMock(),
        agents_dir=".",
    )


def test_http_server_seam_still_exists_in_adk() -> None:
    # GovernedAdkWebServer overrides the private AdkWebServer._create_runner;
    # make sure the seam (and the helper we rely on) still exist upstream.
    assert callable(getattr(AdkWebServer, "_create_runner", None))
    assert callable(getattr(AdkWebServer, "_get_root_agent", None))


def test_http_server_wraps_runner_with_reviewer_enforcement() -> None:
    web_server = _make_web_server()
    agent = _make_agent_with_reviewer()
    raw_runner = MagicMock()

    with patch.object(AdkWebServer, "_create_runner", return_value=raw_runner), \
         patch.object(config, "REVIEWER_ENFORCEMENT", True):
        # _get_root_agent returns non-App inputs unchanged, so passing the
        # agent itself stands in for the App built by get_runner_async.
        runner = web_server._create_runner(agent)

    assert isinstance(runner, ReviewerEnforcementRunner)
    assert isinstance(runner._runner, LoopDetectionRunner)
    assert runner._runner._runner is raw_runner


def test_http_server_toggle_disables_reviewer() -> None:
    web_server = _make_web_server()
    agent = _make_agent_with_reviewer()
    raw_runner = MagicMock()

    with patch.object(AdkWebServer, "_create_runner", return_value=raw_runner), \
         patch.object(config, "REVIEWER_ENFORCEMENT", False):
        runner = web_server._create_runner(agent)

    assert isinstance(runner, LoopDetectionRunner)
    assert not isinstance(runner, ReviewerEnforcementRunner)


@pytest.mark.asyncio
async def test_cli_get_runner_applies_reviewer_enforcement() -> None:
    from orchestrator.app import get_runner, root_agent

    with patch.object(config, "REVIEWER_ENFORCEMENT", True):
        async with get_runner(root_agent) as runner:
            assert isinstance(runner, ReviewerEnforcementRunner)

    with patch.object(config, "REVIEWER_ENFORCEMENT", False):
        async with get_runner(root_agent) as runner:
            assert isinstance(runner, LoopDetectionRunner)
            assert not isinstance(runner, ReviewerEnforcementRunner)
