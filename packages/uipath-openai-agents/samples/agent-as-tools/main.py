import dotenv
from agents import Agent, AgentOutputSchema, Runner, trace
from pydantic import BaseModel, Field
from uipath.tracing import traced

dotenv.load_dotenv()

"""
This example shows the agents-as-tools pattern adapted for UiPath coded agents.
The frontline agent receives a user message and then picks which agents to call,
as tools. In this case, it picks from a set of translation agents.

This sample demonstrates parameter inference - the Input/Output Pydantic models
are automatically extracted to generate rich schemas for UiPath integration.

Based on: https://github.com/openai/openai-agents-python/blob/main/examples/agent_patterns/tools.py
"""


# Required Input/Output models for UiPath coded agents
class TranslationInput(BaseModel):
    """Input model for the translation orchestrator."""

    text: str = Field(description="The English text to translate")
    target_languages: list[str] = Field(
        description="List of target languages (e.g., ['Spanish', 'French', 'Italian'])"
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


spanish_agent = Agent(
    name="spanish_agent",
    instructions="You translate the user's message to Spanish",
    handoff_description="An english to spanish translator",
)

french_agent = Agent(
    name="french_agent",
    instructions="You translate the user's message to French",
    handoff_description="An english to french translator",
)

italian_agent = Agent(
    name="italian_agent",
    instructions="You translate the user's message to Italian",
    handoff_description="An english to italian translator",
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
)


@traced(name="Translation Orchestrator Main")
async def main(input_data: TranslationInput) -> TranslationOutput:
    """
    Main function to orchestrate translations using agent-as-tools pattern.

    This function demonstrates parameter inference - the Input/Output models
    are automatically extracted to generate schemas for UiPath workflows.

    Args:
        input_data: Input containing text and target languages

    Returns:
        TranslationOutput: Result containing translations for requested languages
    """
    print(f"\nTranslating: '{input_data.text}'")
    print(f"Target languages: {', '.join(input_data.target_languages)}\n")

    # Build the prompt based on requested languages
    language_list = ", ".join(input_data.target_languages)
    prompt = f"Translate this text to {language_list}: {input_data.text}"

    with trace("Translation Orchestrator"):
        # Run the orchestrator agent
        result = await Runner.run(
            starting_agent=orchestrator_agent,
            input=[{"content": prompt, "role": "user"}],
        )

        # Extract translations from the response
        # In a real implementation, you'd parse the structured response
        final_response = result.final_output
        print(f"\nAgent response: {final_response}\n")

        # For demonstration, create structured output
        # In production, you'd parse the agent's structured response
        translations = {}
        for lang in input_data.target_languages:
            # Placeholder - in real usage, extract from agent response
            translations[lang] = f"[Translation to {lang}]"

    return TranslationOutput(
        original_text=input_data.text,
        translations=translations,
        languages_used=input_data.target_languages,
    )
