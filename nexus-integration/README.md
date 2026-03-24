# End-to-End (E2E) Integration Tests

This directory contains end-to-end integration tests for the multi-agent orchestration system. These tests verify the seamless communication between the **Root Orchestrator**, the **MCP Server**, and the **A2A Sub-Agents**.

## Overview

The system is a distributed architecture of specialized agents. These tests ensure that the "glue" between these components—transports like SSE and protocols like A2A—is working correctly in a containerized environment.

### Components Under Test

1.  **Root Orchestrator (`projects/orchestrator`)**: The central hub that receives user queries and delegates tasks. It uses the Google ADK and connects to sub-agents via different protocols.
2.  **MCP Server (`projects/mcp_server`)**: A Model Context Protocol (MCP) server providing employee directory tools over Server-Sent Events (SSE).
3.  **A2A Sub-Agent (`projects/a2a_agent`)**: A specialized weather agent following the Agent-to-Agent (A2A) protocol.

---

## Test Structure

### 1. A2A Protocol Health Check (`test_a2a_integration.py`)
- **What it does**: Verifies that the A2A sub-agent is reachable and correctly implements the A2A Discovery protocol.
- **HOW**: It sends an HTTP GET request to the `/.well-known/agent-card.json` endpoint of the A2A agent.
- **WHY**: A2A agents are "pluggable." The Root Orchestrator discovers their capabilities dynamically via this "Business Card." If this endpoint is down or returns an invalid schema, the orchestrator cannot delegate tasks to it.

### 2. Orchestrator Integration Tests (Located in `projects/orchestrator/test_orchestrator.py`)
While not in this directory, these tests are critical for E2E validation:
- **LLM-as-a-Judge**: Uses a high-capability model (e.g., Gemini 2.5 Flash) to evaluate if the Root Orchestrator correctly identified the user's intent and delegated to the right sub-agent.
- **HOW**: It runs the actual agent logic, captures the multi-turn response, and sends the transcript to a "Judge" LLM with a specific rubric.
- **WHY**: Nuanced conversational quality and delegation logic are difficult to test with simple regex or string matching.

---

## How/Why: Architectural Integration

### Why Container-to-Container Testing?
In this project, agents run in separate Docker containers. We test them this way because:
- **Networking**: We need to verify that the Orchestrator can resolve `http://mcp-server:8000` and `http://a2a-agent:8001` using the internal Docker DNS.
- **Environment Isolation**: Sub-agents may have conflicting dependencies (e.g., different versions of Pydantic or specific system libraries for SQLite). Containers allow each agent to have its own optimized runtime.

### How A2A Discovery Works
The Orchestrator is configured with the `A2A_AGENT_URL`. On startup (or first request), it fetches the `agent-card.json`. This card contains:
- **Skills**: What the agent can do (e.g., "Weather Forecast").
- **Examples**: Sample queries to help the Root Orchestrator's LLM understand when to delegate.
- **Endpoints**: Where to send the actual JSON-RPC requests.

---

## Running the Tests

### Prerequisites
1.  Ensure Docker and Docker Compose are installed.
2.  Set your `GEMINI_API_KEY` in the root `.env` file.

### Step 1: Start the Environment
The tests require the full stack to be running and healthy.
```bash
docker-compose up -d --build
```

### Step 2: Run the A2A Integration Test
You can run this test from your host machine if the ports are mapped (default 8001), or from within the orchestrator container.

**From the Host:**
```bash
# Install dependencies first
pip install -r requirements.txt
pytest projects/e2e_tests/test_a2a_integration.py
```

**Inside the Container (Recommended for true network check):**
```bash
docker-compose exec orchestrator pytest /e2e_tests/test_a2a_integration.py
```

### Step 3: Run Orchestrator Performance Tests
To run the "LLM-as-a-Judge" tests:
```bash
docker-compose exec orchestrator pytest test_orchestrator.py
```

---

## Future Roadmap
- **SSE Stream Verification**: Implement tests that listen to the `/run_sse` stream from the orchestrator and assert that specific "thought" or "call" events from the MCP/A2A sub-agents appear in the event stream.
- **Auth Simulation**: Add tests that verify token propagation from the Frontend through the Orchestrator to the Sub-Agents.
