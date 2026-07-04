import asyncio
import httpx
# PYTEST: The standard testing framework for Python.
# EDUCATIONAL NOTE: It makes it easy to write simple, readable tests that can scale 
# to complex functional testing for applications and libraries.
import pytest
import os

# ==========================================
# CONCEPT: Testing Distributed Agents
# EDUCATIONAL NOTE: A2A agents are external services. This test verifies that the running
# A2A container is reachable and communicating properly over HTTP.
# ==========================================

# ASYNCIO MARKER: @pytest.mark.asyncio
# HOW: This decorator tells pytest that the following test function is 
# a coroutine and should be run within an event loop.
# EDUCATIONAL NOTE: Without this, pytest would try to run the function as a normal 
# synchronous function and it would fail.
@pytest.mark.asyncio
async def test_a2a_communication():
    """
    Verifies that the A2A sub-agent is responding to HTTP JSON-RPC requests
    as defined by the A2A protocol.
    """
    # OS.GETENV: Accessing configuration for the test environment.
    a2a_url = os.getenv("A2A_AGENT_URL", "http://localhost:8001")
    
    # STRING MANIPULATION: Normalizing the URL.
    if a2a_url.endswith("agent-card.json"):
        card_url = a2a_url
    else:
        card_url = f"{a2a_url}/.well-known/agent-card.json"
    
    # ASYNC WITH: Using a context manager for the HTTP client.
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(card_url)
            # ASSERT: The core of any test.
            # HOW: 'assert condition, "Error message"'.
            # EDUCATIONAL NOTE: If the condition is False, an AssertionError is raised, 
            # and pytest marks the test as failed.
            assert resp.status_code == 200, f"Failed to get agent card. Ensure A2A container is running at {a2a_url}"
            
            # JSON PARSING: Converting the response body to a Python dictionary.
            card_data = resp.json()
            # ASSERTION: Verifying the content of the response.
            assert card_data["name"] == "Weather Sub-Agent"
            
        except httpx.RequestError as e:
            # PYTEST.FAIL: Explicitly fails the test with a custom message.
            # EDUCATIONAL NOTE: Useful when catching exceptions that should not occur 
            # during a successful test run.
            pytest.fail(f"Connection failed: {e}. Is the A2A container running?")

# MAIN BLOCK: Allows running the test file directly with 'python test_file.py'.
if __name__ == "__main__":
    # ASYNCIO.RUN: Executes the test coroutine.
    asyncio.run(test_a2a_communication())
