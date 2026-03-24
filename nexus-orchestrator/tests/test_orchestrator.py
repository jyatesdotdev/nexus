import asyncio
import os
import sys
import pytest
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Add root directory to path to import the orchestrator package
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from orchestrator.app import root_agent
from orchestrator.config import APP_NAME
from google.adk.runners import InMemoryRunner

# ==========================================
# 1. Evaluation Schema
# ==========================================

class EvalResult(BaseModel):
    """
    Schema for the Judge LLM's evaluation.
    
    WHY: Provides a machine-readable format for test assertions.
    HOW: Pydantic model with pass/fail and reasoning fields.
    """
    score: int = Field(description="Score from 1 to 5")
    reasoning: str = Field(description="Detailed explanation of the score")
    passed: bool = Field(description="Whether the response met the minimum criteria")

# ==========================================
# 2. Judge Implementation
# ==========================================

async def llm_judge(user_query: str, agent_output: str, criteria: str) -> EvalResult:
    """
    Uses a more capable model to evaluate the agent's response.
    
    WHY: LLMs are better at evaluating nuanced conversational quality than regex.
    HOW: Sends a prompt with the rubric to Gemini with structured output.
    """
    client = genai.Client() # Implicitly uses GEMINI_API_KEY from env
    
    prompt = f"""
    You are an expert judge evaluating an AI agent's response.
    
    User Query: {user_query}
    Agent Response: {agent_output}
    Rubric: {criteria}
    
    Evaluate if the agent answered correctly, delegated to the right sub-agent if necessary,
    and followed the instructions.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=EvalResult
        )
    )
    return response.parsed

# ==========================================
# 3. Agent Execution Wrapper
# ==========================================

async def run_agent_test(query: str) -> str:
    """
    Runs the actual agent logic to get a response for the test.
    """
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    user_id = "test_user"
    session_id = f"test_session_{os.urandom(4).hex()}"
    
    await runner.session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    
    full_response = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=query)])
    ):
        if event.author != "user" and not event.partial and event.content:
            for part in event.content.parts:
                if part.text:
                    full_response.append(part.text)
    
    return "\n".join(full_response)

# ==========================================
# 4. Test Cases
# ==========================================

@pytest.mark.asyncio
@pytest.mark.parametrize("query, criteria", [
    ("What is the current CPU usage?", "Should delegate to metric_agent and report a value around 95.4%."),
    ("Check the status of sensor 42", "Should delegate to sensor_agent and report temperature 22.5."),
    ("How much do I have left in my groceries budget?", "Should delegate to api_agent and mention a balance of $150.")
])
async def test_agent_performance(query, criteria):
    """
    End-to-end integration test with LLM-as-a-judge.
    """
    # 1. Get agent response
    response_text = await run_agent_test(query)
    print(f"\n[Test Query]: {query}")
    print(f"[Agent Response]: {response_text}")
    
    # 2. Judge the response
    evaluation = await llm_judge(query, response_text, criteria)
    print(f"[Judge Score]: {evaluation.score}/5")
    print(f"[Judge Reasoning]: {evaluation.reasoning}")
    
    # 3. Assertions
    assert evaluation.passed, f"Agent failed evaluation: {evaluation.reasoning}"
    assert evaluation.score >= 4, f"Agent score too low: {evaluation.score}"

if __name__ == "__main__":
    async def run_demo():
        await test_agent_performance("What is the CPU usage?", "Should mention 95.4%")
    asyncio.run(run_demo())
