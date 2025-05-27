import json

from dotenv import load_dotenv
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
)
from llama_index.llms.openai import OpenAI

from uipath_llamaindex.models import InvokeProcessEvent

load_dotenv()

llm = OpenAI(model="gpt-4o-mini")


async def may_research_company(ctx: Context, company_name: str) -> str:
    """Find whether a company may be researcher.
    Args:
        ctx (Context): The context in which this function is called (autopopulated).
        company_name (str): Name of the company to be researched.
    Returns:
        str: company report
    """
    # emit an event to the external stream to be captured
    ctx.write_event_to_stream(
        InvokeProcessEvent(
            prefix="invoke langgraph researcher event",
            name="my-first-uipath-agent",
            # process_folder_path="(optional)<process-folder-path>",
            input_arguments={
                "topic": company_name,
            },
        )
    )

    # wait until we see a HumanResponseEvent
    hitl_response = await ctx.wait_for_event(HumanResponseEvent)
    feedback = json.loads(hitl_response.response)
    # act on the input from the event
    return feedback["report"]


workflow = AgentWorkflow.from_tools_or_functions(
    [may_research_company],
    llm=llm,
    system_prompt="You are a helpful assistant that can decide whether a company can be researched or not.",
)
