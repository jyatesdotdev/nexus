# orchestrator/registry/ — agent registry

This tiny package implements the registry pattern that decouples sub-agent definitions from the Nexus orchestrator's startup code. Agent modules (see `../agents/`) register factory functions with `@AgentRegistry.register("name")`; `orchestrator/app.py` then instantiates everything with `AgentRegistry.get_all_agents()` when building the root agent. New agents are added by writing a decorated factory in `orchestrator/agents/` — `app.py` does not need to change.

## Files

- `__init__.py` — Empty.
- `agent_registry.py` — The `AgentRegistry` class. All state is a single class-level dict `_agents: Dict[str, Callable]` mapping agent name -> zero-arg factory. Key behaviors and invariants:
  - `register(name)` is a decorator factory. Registration happens at module IMPORT time, so a factory only exists in the registry if its module has been imported. Registering the same name twice silently overwrites the first — names must be unique.
  - `get_all_agents()` calls every factory fresh each time; factories must be safe to call repeatedly and must return a new agent instance (ADK agents cannot be shared between parents).
  - `clear()` empties the registry; `orchestrator/app.py` calls it at the top of `initialize_agents()` so re-initialization (e.g. in tests) does not accumulate duplicates.
  - `load_agents_from_module(package_name)` imports the named target (or, if already in `sys.modules`, RELOADS it via `importlib.reload`). The reload is deliberate: after `clear()`, decorators must re-execute to repopulate the registry. It then walks and (re)imports every submodule via `pkgutil.walk_packages` ONLY IF the argument names a *package* (has a `__path__`). NOTE: the sole production caller (`app.py`) passes the *module* `orchestrator.agents.core_agents`, which has no `__path__`, so the walk branch is not taken today — only `core_agents.py` is (re)loaded through this path, and its module-level code runs once per `initialize_agents()` call. Keep agent modules side-effect-free apart from registration.
  - The registry stores factories for both `LlmAgent` and `RemoteA2aAgent` products; it is intentionally untyped beyond `Callable[[], Any]`.

## How to test

There is no dedicated test file for the registry; it is exercised indirectly:

```bash
cd <workspace-root>/nexus-orchestrator
uv run pytest tests/test_initialization.py tests/test_orchestrator.py
```

## Caution

- The class-level dict is shared global state across the whole process. Never mutate `_agents` directly; use `register`/`clear`.
- Do not remove the reload logic in `load_agents_from_module` — tests that reload `orchestrator.app` depend on decorators re-running after `clear()`.
