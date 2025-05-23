from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
)
from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-4o-mini")


async def research_company(ctx: Context) -> str:
    """Research a company."""
    print("Researching company...")

    # emit an event to the external stream to be captured
    ctx.write_event_to_stream(
        InputRequiredEvent(prefix="Are you sure you want to proceed?")
    )

    # wait until we see a HumanResponseEvent
    response = await ctx.wait_for_event(HumanResponseEvent)
    print("Received response:", response.response)

    # act on the input from the event
    if response.response.strip().lower() == "yes":
        return "Research completed successfully."
    else:
        return "Research task aborted."


workflow = AgentWorkflow.from_tools_or_functions(
    [research_company],
    llm=llm,
    system_prompt="You are a helpful assistant that can research companies.",
)
