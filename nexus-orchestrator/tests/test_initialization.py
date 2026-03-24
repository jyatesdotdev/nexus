import os
import sys
from unittest.mock import patch

# Add root directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_multi_agent_initialization():
    # Mock environment variables for multiple MCP and A2A agents
    mock_env = {
        "MCP_SERVER_URLS": "http://mcp1:8000/sse,http://mcp2:8000/sse",
        "A2A_AGENT_URLS": "http://a2a1:8001/card.json,http://a2a2:8001/card.json,http://a2a3:8001/card.json",
        "GEMINI_API_KEY": "dummy_key"
    }
    
    with patch.dict(os.environ, mock_env):
        # We need to reload the config module to pick up the new env vars
        import importlib
        import orchestrator.config
        importlib.reload(orchestrator.config)
        
        import orchestrator.app
        importlib.reload(orchestrator.app)
        
        from orchestrator.app import initialize_agents
        root_agent = initialize_agents()
        
        sub_agent_names = [agent.name for agent in root_agent.sub_agents]
        print(f"Sub-agent names: {sub_agent_names}")
        
        # Core agents: sensor_agent, metric_agent, api_agent, parsing_agent, system_agent (5)
        # MCP agents: mcp_agent_0, mcp_agent_1 (2)
        # A2A agents: a2a_agent_0, a2a_agent_1, a2a_agent_2 (3)
        # Total: 10
        
        assert "sensor_agent" in sub_agent_names
        assert "metric_agent" in sub_agent_names
        assert "api_agent" in sub_agent_names
        assert "parsing_agent" in sub_agent_names
        assert "system_agent" in sub_agent_names
        
        assert "mcp_agent_0" in sub_agent_names
        assert "mcp_agent_1" in sub_agent_names
        
        assert "a2a_agent_0" in sub_agent_names
        assert "a2a_agent_1" in sub_agent_names
        assert "a2a_agent_2" in sub_agent_names
        
        assert len(sub_agent_names) == 10
