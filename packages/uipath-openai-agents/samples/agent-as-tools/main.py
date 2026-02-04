from agents import Agent, AgentOutputSchema, RunContextWrapper, function_tool
from agents.models import _openai_shared
from pydantic import BaseModel, Field

from uipath_openai_agents.chat import UiPathChatOpenAI
from uipath_openai_agents.chat.supported_models import OpenAIModels

"""
This example shows the agents-as-tools pattern adapted for UiPath coded agents.
The frontline agent receives a user message and then picks which agents to call,
as tools. In this case, it picks from a set of translation agents.

This sample demonstrates:
- Parameter inference: Input/Output Pydantic models are automatically extracted
- Context passing: A Context model provides data accessible to tools (not sent to LLM)

Based on: https://github.com/openai/openai-agents-python/blob/main/examples/agent_patterns/tools.py
"""


class InputModel(BaseModel):
    """Context data accessible to tools (not sent to LLM).

    The 'messages' field is always separate and goes to the LLM.
    These fields are passed to tools via RunContextWrapper.
    """

    user_id: str = Field(default="anonymous", description="User identifier for logging")
    preferred_formality: str = Field(
        default="formal",
        description="Translation formality level: 'formal' or 'informal'",
    )


class TranslationOutput(BaseModel):
    """Output model for the translation orchestrator."""

    original_text: str = Field(description="The original English text")
    translations: dict[str, str] = Field(
        description="Dictionary mapping language names to translated text"
    )
    languages_used: list[str] = Field(
        description="List of languages that were translated to"
    )


@function_tool
def get_translation_preferences(ctx: RunContextWrapper[InputModel]) -> str:
    """Get the user's translation preferences from context."""
    return (
        f"User {ctx.context.user_id} prefers {ctx.context.preferred_formality} "
        f"translations."
    )


def main() -> Agent[InputModel]:
    """Configure UiPath OpenAI client and return the orchestrator agent."""
    # Configure UiPath OpenAI client for agent execution
    # This routes all OpenAI API calls through UiPath's LLM Gateway
    MODEL = OpenAIModels.gpt_5_1_2025_11_13
    uipath_openai_client = UiPathChatOpenAI(model_name=MODEL)
    _openai_shared.set_default_openai_client(uipath_openai_client.async_client)

    # Define specialized translation agents
    spanish_agent = Agent[InputModel](
        name="spanish_agent",
        instructions="You translate the user's message to Spanish",
        handoff_description="An english to spanish translator",
        model=MODEL,
    )

    french_agent = Agent[InputModel](
        name="french_agent",
        instructions="You translate the user's message to French",
        handoff_description="An english to french translator",
        model=MODEL,
    )

    italian_agent = Agent[InputModel](
        name="italian_agent",
        instructions="You translate the user's message to Italian",
        handoff_description="An english to italian translator",
        model=MODEL,
    )

    # Orchestrator agent that uses other agents as tools
    # Uses output_type for structured outputs (native OpenAI Agents pattern)
    # Note: Using AgentOutputSchema with strict_json_schema=False because
    # dict[str, str] is not compatible with OpenAI's strict JSON schema mode
    orchestrator_agent = Agent[InputModel](
        name="orchestrator_agent",
        instructions=(
            "You are a translation agent. You use the tools given to you to translate. "
            "If asked for multiple translations, you call the relevant tools in order. "
            "You never translate on your own, you always use the provided tools. "
            "Before translating, check the user's preferences using get_translation_preferences."
        ),
        tools=[
            get_translation_preferences,
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
