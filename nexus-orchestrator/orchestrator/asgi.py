from orchestrator.app import root_agent, session_service, memory_service
from orchestrator.server import create_app_instance

app = create_app_instance(root_agent, session_service, memory_service)
