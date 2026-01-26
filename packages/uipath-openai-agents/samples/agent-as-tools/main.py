from agents import Agent, AgentOutputSchema
from agents.models import _openai_shared
from pydantic import BaseModel, Field

from uipath_openai_agents.chat import UiPathChatOpenAI
from uipath_openai_agents.chat.supported_models import OpenAIModels

"""
This example shows the agents-as-tools pattern adapted for UiPath coded agents.
The frontline agent receives a user message and then picks which agents to call,
as tools. In this case, it picks from a set of translation agents.

This sample demonstrates parameter inference - the Input/Output Pydantic models
are automatically extracted to generate rich schemas for UiPath integration.

Based on: https://github.com/openai/openai-agents-python/blob/main/examples/agent_patterns/tools.py
"""


class TranslationOutput(BaseModel):
    """Output model for the translation orchestrator."""

    original_text: str = Field(description="The original English text")
    translations: dict[str, str] = Field(
        description="Dictionary mapping language names to translated text"
    )
    languages_used: list[str] = Field(
        description="List of languages that were translated to"
    )


def main() -> Agent:
    """Configure UiPath OpenAI client and return the orchestrator agent."""
    # Configure UiPath OpenAI client for agent execution
    # This routes all OpenAI API calls through UiPath's LLM Gateway
    MODEL = OpenAIModels.gpt_5_1_2025_11_13
    uipath_openai_client = UiPathChatOpenAI(model_name=MODEL)
    _openai_shared.set_default_openai_client(uipath_openai_client.async_client)

    # Define specialized translation agents
    spanish_agent = Agent(
        name="spanish_agent",
        instructions="You translate the user's message to Spanish",
        handoff_description="An english to spanish translator",
        model=MODEL,
    )

    french_agent = Agent(
        name="french_agent",
        instructions="You translate the user's message to French",
        handoff_description="An english to french translator",
        model=MODEL,
    )

    italian_agent = Agent(
        name="italian_agent",
        instructions="You translate the user's message to Italian",
        handoff_description="An english to italian translator",
        model=MODEL,
    )

    # Orchestrator agent that uses other agents as tools
    # Uses output_type for structured outputs (native OpenAI Agents pattern)
    # Note: Using AgentOutputSchema with strict_json_schema=False because
    # dict[str, str] is not compatible with OpenAI's strict JSON schema mode
    orchestrator_agent = Agent(
        name="orchestrator_agent",
        instructions=(
            "You are a translation agent. You use the tools given to you to translate. "
            "If asked for multiple translations, you call the relevant tools in order. "
            "You never translate on your own, you always use the provided tools."
        ),
        tools=[
            spanish_agent.as_tool(
                tool_name="translate_to_spanish",
                tool_description="Translate the user's message to Spanish",
            ),
            french_agent.as_tool(
                tool_name="translate_to_french",
                tool_description="Translate the user's message to French",
            ),
            italian_agent.as_tool(
                tool_name="translate_to_italian",
                tool_description="Translate the user's message to Italian",
            ),
        ],
        output_type=AgentOutputSchema(TranslationOutput, strict_json_schema=False),
        model=MODEL,
    )

    return orchestrator_agent
