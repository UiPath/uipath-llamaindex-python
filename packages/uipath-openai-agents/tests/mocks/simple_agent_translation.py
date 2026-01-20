"""Simple OpenAI agent for testing - translation agent with custom output."""

from agents import Agent
from pydantic import BaseModel, Field


class TranslationOutput(BaseModel):
    """Output model for translation."""

    original_text: str = Field(description="The original text")
    translated_text: str = Field(description="The translated text")
    target_language: str = Field(description="The target language")


# Agent with custom output type (direct Pydantic model)
agent = Agent(
    name="translation_agent",
    instructions="You are a translation agent. Translate the given text to the target language specified in the message.",
    output_type=TranslationOutput,
)
