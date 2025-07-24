from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
)

from uipath_llamaindex.llms import UiPathOpenAI

llm = UiPathOpenAI(model="gpt-4o-mini-2024-07-18")


async def may_research_company(ctx: Context, company_name: str) -> bool:
    """Find whether a company may be researched.
    Args:
        ctx (Context): The context in which this function is called (autopopulated).
        company_name (str): Name of the company to be researched.
    Returns:
        bool: True if the company can be researched, False otherwise.
    """
    print("Researching company...")

    # emit an event to the external stream to be captured
    ctx.write_event_to_stream(
        InputRequiredEvent(
            prefix=f"May I perform a research on company {company_name}? \n (yes/no)"
        )
    )

    # wait until we see a HumanResponseEvent
    response = await ctx.wait_for_event(HumanResponseEvent)
    print("Received response:", response.response)

    # act on the input from the event
    if response.response.strip().lower() == "yes":
        return True
    else:
        return False


workflow = AgentWorkflow.from_tools_or_functions(
    [may_research_company],
    llm=llm,
    system_prompt="You are a helpful assistant that can decide whether a company can be researched or not.",
)
