# EDUCATIONAL NOTE: A Dedicated ASGI Module Makes App Construction Happen Once
# Gunicorn is given a module path ("orchestrator.asgi:app"), not a function to
# call, so whatever that module does at import time IS the worker's startup.
# Importing root_agent/session_service here means the agent tree and
# persistence backends are built exactly once per worker process, then reused
# for every request. Routing production through `cli serve` instead would drag
# Click and argument parsing into the serving path and leave two subtly
# different ways to boot the app; this module keeps the production import
# graph minimal and deterministic.
from orchestrator.app import root_agent, session_service, memory_service
from orchestrator.server import create_app_instance

app = create_app_instance(root_agent, session_service, memory_service)
