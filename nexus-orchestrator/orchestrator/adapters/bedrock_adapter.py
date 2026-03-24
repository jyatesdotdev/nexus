import os
# ASYNCGENERATOR: A type hint for functions that use 'yield' within an 'async def' block.
# WHY: This allows us to stream data asynchronously. Instead of waiting for 
# a full response from an LLM, we can yield parts as they arrive.
from typing import AsyncGenerator
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# ADAPTER PATTERN: BedrockAdapter converts the interface of a third-party API 
# (Amazon Bedrock) into the interface expected by the ADK (BaseLlm).
# WHY: This design allows the rest of the application to remain agnostic 
# of which specific LLM provider is being used.
class BedrockAdapter(BaseLlm):
    """
    CONCEPT: Foundation Model Abstraction
    
    WHY: The Google ADK orchestrator is not locked into Gemini. You can plug in 
    any foundation model (OpenAI, Anthropic, local OSS models) by implementing 
    the `BaseLlm` interface.
    """
    
    # CLASS ATTRIBUTE: Shared by all instances of the class.
    model: str = "anthropic.claude-3-sonnet-20240229-v1:0"

    # CLASSMETHOD: A decorator that defines a method bound to the class, not an instance.
    # HOW: The first argument 'cls' refers to the class itself (BedrockAdapter).
    # WHY: This is used here as a "factory-like" mechanism to tell the ADK which 
    # model names this specific adapter is capable of handling.
    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"anthropic\.claude-.*"]

    # ASYNC GENERATOR: A function that uses 'async def' and 'yield'.
    # HOW: It returns an AsyncGenerator object.
    # WHY: Essential for "streaming" LLM responses, providing a better user 
    # experience by showing text as it is generated rather than all at once.
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        """
        Implementation of the asynchronous content generation for Amazon Bedrock.
        """
        
        # YIELD: Returns a value but remembers the function's state to resume later.
        # WHY: This allows the caller to iterate over the generator and get 
        # multiple 'LlmResponse' objects over time.
        yield LlmResponse(
            partial=False,
            content=types.Content(
                role="model", 
                parts=[types.Part(text="This is a response from the Bedrock adapter.")]
            )
        )
