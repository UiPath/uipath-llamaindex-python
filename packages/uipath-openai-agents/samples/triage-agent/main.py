from agents import Agent
from agents.models import _openai_shared
from pydantic import BaseModel

from uipath_openai_agents.chat import UiPathChatOpenAI
from uipath_openai_agents.chat.supported_models import OpenAIModels

"""
This example shows the handoffs/routing pattern adapted for UiPath coded agents.
The triage agent receives the first message, and then hands off to the appropriate
agent based on the language of the request. Responses are streamed to the user.

Based on: https://github.com/openai/openai-agents-python/blob/main/examples/agent_patterns/routing.py
"""


class Output(BaseModel):
    """Output model for the routing agent."""

    response: str
    agent_used: str


def main() -> Agent:
    """Configure UiPath OpenAI client and return the triage agent."""
    # Configure UiPath OpenAI client for agent execution
    # This routes all OpenAI API calls through UiPath's LLM Gateway
    MODEL = OpenAIModels.gpt_5_1_2025_11_13
    uipath_openai_client = UiPathChatOpenAI(model_name=MODEL)
    _openai_shared.set_default_openai_client(uipath_openai_client.async_client)

    # Define specialized agents for different languages
    french_agent = Agent(
        name="french_agent",
        instructions="You only speak French",
        model=MODEL,
    )

    spanish_agent = Agent(
        name="spanish_agent",
        instructions="You only speak Spanish",
        model=MODEL,
    )

    english_agent = Agent(
        name="english_agent",
        instructions="You only speak English",
        model=MODEL,
    )

    # Triage agent routes to appropriate language agent
    triage_agent = Agent(
        name="triage_agent",
        instructions="Handoff to the appropriate agent based on the language of the request.",
        handoffs=[french_agent, spanish_agent, english_agent],
        model=MODEL,
    )

    return triage_agent
