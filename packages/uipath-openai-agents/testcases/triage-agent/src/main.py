"""
Integration testcase for the triage/routing pattern.
The triage agent receives a message and hands off to the appropriate
agent based on the language of the request.

"""

from agents import Agent
from agents.models import _openai_shared

from uipath_openai_agents.chat import UiPathChatOpenAI


def main() -> Agent:
    """Configure UiPath OpenAI client and return the triage agent."""
    # Configure UiPath OpenAI client for agent execution
    # This routes all OpenAI API calls through UiPath's LLM Gateway
    MODEL = "gpt-4o-2024-11-20"
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
    # Entry point - messages come in as JSON and are handled directly by the agent
    agent = Agent(
        name="triage_agent",
        instructions="Handoff to the appropriate agent based on the language of the request.",
        handoffs=[french_agent, spanish_agent, english_agent],
        model=MODEL,
    )

    return agent
