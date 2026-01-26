"""RAG Assistant sample - Basic Agent with Chat.

This sample demonstrates a basic OpenAI agent using the Agents SDK framework with direct OpenAI client.

Features:
- OpenAI Agents SDK integration
- Direct OpenAI API client usage
- Type-safe input/output with Pydantic models
- Streaming responses support
"""

from agents import Agent


def main() -> Agent:
    """Return the assistant agent."""
    MODEL = "gpt-5.1-2025-11-13"

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
