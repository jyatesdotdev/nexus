import importlib
import pkgutil
from typing import Callable, Dict, Any, Type, List, Optional
from google.adk.agents.llm_agent import LlmAgent as Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

class AgentRegistry:
    """
    EDUCATIONAL NOTE: Registry Pattern
    [Why] Decouples agent definition from the central orchestrator's initialization logic.
    New agents can be added by simply defining them and registering them here, rather than
    modifying `app.py`.
    """
    _agents: Dict[str, Callable[[], Any]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        """Decorator to register a function that creates an agent."""
        def wrapper(func: Callable[[], Any]) -> Callable[[], Any]:
            cls._agents[name] = func
            return func
        return wrapper

    @classmethod
    def clear(cls) -> None:
        """Clears all registered agents. Useful for testing."""
        cls._agents.clear()

    @classmethod
    def get_all_agents(cls) -> List[Any]:
        """Instantiates and returns all registered agents."""
        agents = []
        for name, factory in cls._agents.items():
            agents.append(factory())
        return agents

    @classmethod
    def load_agents_from_module(cls, package_name: str) -> None:
        """
        Dynamically imports all modules within a given package to ensure
        the @AgentRegistry.register decorators are executed.
        """
        import sys
        
        # If the package is already loaded (e.g. during a test reload), we must reload it
        # so the decorators re-execute after a registry clear.
        if package_name in sys.modules:
            package = importlib.reload(sys.modules[package_name])
        else:
            package = importlib.import_module(package_name)
            
        if hasattr(package, '__path__'):
            for _, module_name, _ in pkgutil.walk_packages(
                package.__path__, package.__name__ + "."
            ):
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)
