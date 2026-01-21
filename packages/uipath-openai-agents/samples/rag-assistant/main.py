"""RAG Assistant sample - Basic Agent with Chat.

This sample demonstrates a basic OpenAI agent using the Agents SDK framework with UiPath integration.

Features:
- OpenAI Agents SDK integration
- UiPath tracing with OpenTelemetry
- Type-safe input/output with Pydantic models
- Streaming responses support
"""

from agents import Agent
from agents.models import _openai_shared
from pydantic import BaseModel, Field
from uipath_openai_agents.chat import UiPathChatOpenAI


def main() -> Agent:
    """Configure UiPath OpenAI client and return the assistant agent."""
    # Configure UiPath OpenAI client for agent execution
    # This routes all OpenAI API calls through UiPath's LLM Gateway
    MODEL = "gpt-4o-2024-11-20"
    uipath_openai_client = UiPathChatOpenAI(model_name=MODEL)
    _openai_shared.set_default_openai_client(uipath_openai_client.async_client)

    # Define the assistant agent
    assistant_agent = Agent(
        name="assistant_agent",
        instructions="""You are a helpful AI assistant that provides clear, concise answers.

Your capabilities:
- Answer questions accurately
- Provide well-structured responses
- Be helpful and informative

Always aim for clarity and accuracy in your responses.""",
        model=MODEL,
    )

    return assistant_agent
    return assistant_agent
