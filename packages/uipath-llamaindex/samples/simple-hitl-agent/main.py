from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
)
from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-4o-mini")


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
    system_prompt="""You are a helpful assistant that researches companies.

CRITICAL: You MUST call the may_research_company function BEFORE providing any information about a company. After calling the function and receiving approval, provide your research summary.""",
)
