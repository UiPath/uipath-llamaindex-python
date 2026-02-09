from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
)

from uipath_llamaindex.llms import UiPathOpenAI

llm = UiPathOpenAI()


async def may_research_company(ctx: Context, company_name: str) -> bool:
    """Find whether a company may be researched.
    Args:
        ctx (Context): The context in which this function is called (autopopulated).
        company_name (str): Name of the company to be researched.
    Returns:
        bool: True if the company can be researched, False otherwise.
    """
    print("Researching company...")

    question = f"May I perform research on company '{company_name}'? (yes/no) "

    # wait until we see a HumanResponseEvent
    response = await ctx.wait_for_event(
        HumanResponseEvent,
        waiter_id=question,
        waiter_event=InputRequiredEvent(
            prefix=question,
        ),
    )
    print("Received response:", response.response)

    # act on the input from the event
    if response.response.strip().lower() == "yes":
        return True
    else:
        return False


workflow = FunctionAgent(
    tools=[may_research_company],
    llm=llm,
    system_prompt=(
        "You are a helpful assistant that researches companies. "
        "You MUST call may_research_company before providing any information."
    ),
)
