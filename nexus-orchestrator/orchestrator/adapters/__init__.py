# EDUCATIONAL NOTE: Adapter registration via package import side effects.
# [Why] `orchestrator/app.py` does `from . import adapters` expecting that to
# register every custom model backend with ADK's LLMRegistry. Registration
# happens as a module-level side effect (`LLMRegistry.register(...)`) inside
# each adapter module, so those modules must actually be imported here —
# otherwise `AGENT_MODEL=ollama/...` fails with an unknown-model error.
# The bedrock adapter is a skeletal stub (no boto3 / AWS calls at import time
# and no LLMRegistry registration); importing it is harmless and keeps the
# package self-documenting.
from . import ollama_adapter
from . import bedrock_adapter

__all__ = ["ollama_adapter", "bedrock_adapter"]
