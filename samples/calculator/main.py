from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from uipath_llamaindex.llms import UiPathOpenAI


def multiply(a: float, b: float) -> float:
    """Useful for multiplying two numbers."""
    return a * b


def add(a: float, b: float) -> float:
    """Useful for adding two numbers."""
    return a + b


# Define events for the workflow
class UserQueryEvent(StartEvent):
    """Event representing a user query to the calculator agent."""

    query: str


class CalculatorResponseEvent(StopEvent):
    """Event representing the calculator agent's response."""

    response: str


# Define the workflow
class CalculatorAgentWorkflow(Workflow):
    """Workflow that uses calculator tools to respond to math queries."""

    @step
    async def process_query(self, ev: UserQueryEvent) -> CalculatorResponseEvent:
        """Process the user query using the calculator agent."""

        # Initialize the agent with calculator tools
        agent = FunctionAgent(
            name="Calculator Agent",
            description="An agent that can add and multiply numbers",
            llm=UiPathOpenAI(model="gpt-4o-2024-11-20"),
            tools=[multiply, add],
            system_prompt="You are a helpful assistant that can multiply and add numbers.",
        )

        # Run the agent with the user's query
        response = await agent.run(user_msg=ev.query)

        return CalculatorResponseEvent(response=str(response))


# Export the workflow instance for uipath CLI
workflow = CalculatorAgentWorkflow(timeout=300, verbose=True)
