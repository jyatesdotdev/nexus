import asyncio
from typing import Optional
import click
import uvicorn
from google.genai.types import Content, Part

from orchestrator.config import (
    APP_NAME,
    DEFAULT_SESSION_ID,
    DEFAULT_USER_ID,
    validate_config,
)
from orchestrator.app import root_agent, session_service, memory_service, get_runner, run_chat_loop

# EDUCATIONAL NOTE: One Construction Path, Three Front Doors
# chat, serve, and evals all import the SAME root_agent/session_service/
# get_runner from orchestrator.app rather than building their own. That is
# deliberate: the terminal chat loop, the HTTP server, and the eval harness
# exercise an identical runner pipeline (Runner -> LoopDetection -> Reviewer),
# so a behavior verified in `chat` cannot silently differ under `serve`. The
# Click *group* callback is also a teaching point — it runs before ANY
# subcommand, making validate_config() a single choke point for failing fast
# on missing environment instead of repeating the check per command.
@click.group()
def cli() -> None:
    """Multi-Agent Orchestrator CLI."""
    validate_config()


@cli.command()
@click.argument("prompt", required=False)
def chat(prompt: Optional[str]) -> None:
    """Start an interactive chat or run a single prompt."""
    asyncio.run(run_chat_loop(prompt))


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind.")
@click.option("--port", default=8080, help="Port to bind.")
def serve(host: str, port: int) -> None:
    """Start the FastAPI backend server."""
    from orchestrator.server import create_app_instance
    app = create_app_instance(root_agent, session_service, memory_service)
    uvicorn.run(app, host=host, port=port)

@cli.command()
def evals() -> None:
    """Run LLM evaluations to measure accuracy and routing."""
    from orchestrator.eval_cases import EVAL_CASES
    
    async def run_evals():
        print("🧪 Starting Nexus LLM Evaluations...")
        results = []
        for case in EVAL_CASES:
            print(f"Running Case: {case.name} - {case.input}")
            
            # Ensure session exists to prevent SessionNotFoundError
            if not await session_service.get_session(
                app_name=APP_NAME, user_id=DEFAULT_USER_ID, session_id=DEFAULT_SESSION_ID
            ):
                await session_service.create_session(
                    app_name=APP_NAME, user_id=DEFAULT_USER_ID, session_id=DEFAULT_SESSION_ID
                )

            async with get_runner(root_agent) as runner:
                full_response = ""
                routed_agent = None
                error_occurred = False
                
                try:
                    async for event in runner.run_async(
                        user_id=DEFAULT_USER_ID,
                        session_id=DEFAULT_SESSION_ID,
                        new_message=Content(parts=[Part(text=case.input)]),
                    ):
                        # Tracking routing
                        if event.actions and event.actions.transfer_to_agent:
                             routed_agent = event.actions.transfer_to_agent
                        elif hasattr(event, "author") and event.author:
                             routed_agent = event.author

                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if part.text:
                                    full_response += part.text
                except Exception as e:
                    print(f"ERROR running case {case.name}: {e}")
                    error_occurred = True
                
                # Evaluation logic
                if error_occurred:
                    status = "❌ ERROR"
                    routing_pass = False
                    keyword_pass = False
                else:
                    # 1. Routing Correctness
                    routing_pass = case.expected_agent in (routed_agent or "") or routed_agent == case.expected_agent
                    
                    # 2. Keyword Coverage
                    keyword_pass = all(k.lower() in full_response.lower() for k in case.expected_keywords)
                    
                    status = "✅ PASS" if routing_pass and keyword_pass else "❌ FAIL"
                
                results.append({
                    "name": case.name,
                    "status": status,
                    "routed": routed_agent,
                    "routing_pass": routing_pass,
                    "keyword_pass": keyword_pass
                })
                print(f"Result: {status} (Routed to: {routed_agent})")
        
        # Summary
        passed = sum(1 for r in results if r["status"] == "✅ PASS")
        print("\n" + "="*40)
        print(f"Evaluation Summary: {passed}/{len(results)} Passed")
        print("="*40)
        for r in results:
             print(f"{r['status']} | {r['name']:25} | Routed: {r['routed']}")

    asyncio.run(run_evals())
