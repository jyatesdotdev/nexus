# Changelog - Nexus Integration Tests

## [Routing E2E + CI] - 2026-07-04
- **New test:** Added `test_routing_integration.py` — true end-to-end routing checks
  against a live stack via the orchestrator's `POST /run_sse` SSE endpoint. A weather
  prompt must be delegated to `weather_a2a_agent` and an HR prompt to `mcp_agent`;
  delegation is asserted from event `author` fields and `actions.transferToAgent`, plus a
  non-empty final answer, all under a hard 120 s stream timeout. Configurable via
  `ORCHESTRATOR_URL` (default `http://localhost:8080`); skips cleanly (`pytest.skip`)
  when `/health` is unreachable, so stackless runs stay green.
- **CI:** The workspace gained `.github/workflows/ci.yml` (path-filtered per-service
  lint/type-check/unit tests, Semgrep, static Checkov). This directory's stack-dependent
  suite — including the new routing test — is intentionally excluded from CI and remains
  a local/`nexus-stack` concern.
- **Docs:** Updated `README.md` and `AGENTS.md` for the new test, `ORCHESTRATOR_URL`,
  and the CI exclusion; noted that `nexus-stack/Makefile`'s `test` target does not yet
  enumerate the new file.

## [Refinement] - 2026-07-03
- **Docs:** Rewrote `README.md` to describe the current polyrepo reality: the two test
  files that exist (`test_a2a_integration.py`, `test_persistence_integration.py`) and
  how they run inside the orchestrator container (mounted at `/e2e_tests`) via
  `make test` from `../nexus-stack`. Removed references to the dead `projects/` monorepo
  layout, a nonexistent `requirements.txt`, and the old `test_orchestrator.py` filename.
- **Cleanup:** Removed the unused `from google.genai import types` import from
  `test_a2a_integration.py`, dropping the pointless `google-genai` dependency for
  host-side runs.

## [Initial State] - 2026-03-21
- **Strategy:** Researched and implemented "LLM-as-a-judge" for testing agentic workflows.
- **Implementation:** Created automated `pytest` cases that use Gemini to evaluate agent quality.
- **Validation:** Verified all agents (sensor, metric, api) pass high-quality evaluation rubrics.

## [A2A Capability] - 2026-03-21
- **Testing:** Implemented `test_a2a_integration.py` to verify the multi-agent handshake and message exchange.
