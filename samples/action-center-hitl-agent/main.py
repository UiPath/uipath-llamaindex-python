import json

from dotenv import load_dotenv
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
)
from llama_index.llms.openai import OpenAI

from uipath_llamaindex.models import CreateActionEvent

load_dotenv()

llm = OpenAI(model="gpt-4o-mini")


async def may_research_company(ctx: Context, company_name: str) -> bool:
    """Find whether a company may be researched.
    Args:
        ctx (Context): The context in which this function is called (autopopulated).
        company_name (str): Name of the company to be researched.
    Returns:
        bool: True if the company can be researched, False otherwise.
    """
    # emit an event to the external stream to be captured
    agent_name = "Company researcher"
    ctx.write_event_to_stream(
        CreateActionEvent(
            prefix="hitl escalation to research company",
            app_name="generic_escalation_app",
            title=f"Action required for {agent_name}",
            data={
                "AgentOutput": (f"May I perform a research on company {company_name}?"),
                "AgentName": agent_name,
            },
            app_version=1,
            app_folder_path="Shared",
            # assignee="(optional)<assignee email>"
        )
    )

    # wait until we see a HumanResponseEvent
    hitl_response = await ctx.wait_for_event(HumanResponseEvent)
    feedback = json.loads(hitl_response.response)
    # act on the input from the event
    if isinstance(feedback["Answer"], bool) and feedback["Answer"] is True:
        return True
    else:
        return False


# example user input {"user_msg": "research Uipath company"}
workflow = AgentWorkflow.from_tools_or_functions(
    [may_research_company()],
    llm=llm,
    system_prompt="You are a helpful assistant that can use tools to perform actions requested by user",
)
