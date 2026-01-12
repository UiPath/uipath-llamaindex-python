"""RAG Assistant sample - Iteration 1: Basic Agent with Chat.

This sample uses the OpenAI Agents SDK framework with UiPath integration.
It will be enhanced in subsequent iterations with:
- Iteration 2: OpenTelemetry tracing
- Iteration 3: Breakpoints for debugging
- Iteration 4: Embeddings for document processing
- Iteration 5: Context Grounding retriever
- Iteration 6: Full RAG query engine
"""

import dotenv
from agents import Agent, Runner
from pydantic import BaseModel, Field
from uipath.tracing import traced

dotenv.load_dotenv()


# Required Input/Output models for UiPath coded agents
class Input(BaseModel):
    """Input model for the RAG assistant."""

    question: str = Field(description="The question to ask the assistant")


class Output(BaseModel):
    """Output model for the RAG assistant."""

    answer: str = Field(description="The assistant's answer")
    agent_used: str = Field(description="The name of the agent that answered")


# Define the assistant agent
assistant_agent = Agent(
    name="assistant_agent",
    instructions="""You are a helpful AI assistant that provides clear, concise answers.

Your capabilities:
- Answer questions accurately
- Provide well-structured responses
- Cite sources when applicable (future: will use RAG)

Be helpful and informative.""",
)


@traced(name="RAG Assistant Main")
async def main(input_data: Input) -> Output:
    """Main function for RAG assistant using OpenAI Agents SDK.

    This function demonstrates the basic OpenAI Agents pattern with UiPath integration.

    Args:
        input_data: Input containing the question to ask

    Returns:
        Output: Result containing the answer and agent used
    """
    print(f"\n🔍 Question: {input_data.question}\n")

    # Run the assistant agent (non-streaming for simplicity)
    result = await Runner.run(
        starting_agent=assistant_agent,
        input=[{"content": input_data.question, "role": "user"}],
    )

    # Extract the final response
    final_response = result.final_output
    agent_used = result.current_agent.name

    print(f"\n💬 Answer: {final_response}")
    print(f"✅ Agent used: {agent_used}\n")

    return Output(answer=final_response, agent_used=agent_used)
