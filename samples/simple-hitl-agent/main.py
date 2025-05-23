from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
)
from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-4o-mini")


# a tool that performs a dangerous task
async def dangerous_task(ctx: Context) -> str:
    """A dangerous task that requires human confirmation."""

    # emit an event to the external stream to be captured
    ctx.write_event_to_stream(
        InputRequiredEvent(
            prefix="Are you sure you want to proceed? ",
            user_name="Laurie",
        )
    )

    # wait until we see a HumanResponseEvent
    response = await ctx.wait_for_event(
        HumanResponseEvent, requirements={"user_name": "Laurie"}
    )

    # act on the input from the event
    if response.response.strip().lower() == "yes":
        return "Dangerous task completed successfully."
    else:
        return "Dangerous task aborted."


workflow = AgentWorkflow.from_tools_or_functions(
    [dangerous_task],
    llm=llm,
    system_prompt="You are a helpful assistant that can perform dangerous tasks.",
)
