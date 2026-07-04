# Changelog - Nexus Integration Tests

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
