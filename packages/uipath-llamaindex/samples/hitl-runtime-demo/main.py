import asyncio

from dotenv import load_dotenv
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.agent.workflow.function_agent import FunctionAgent
from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
)
from llama_index.llms.openai import OpenAI

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
    ctx.write_event_to_stream(
        InputRequiredEvent(
            prefix=f"May I perform a research on company {company_name}? (yes/no)"
        )
    )

    response = await ctx.wait_for_event(HumanResponseEvent)
    print("Received response:", response.response)

    return response.response.strip().lower() == "yes"


agent = FunctionAgent(
    name="Agent",
    description="A single agent that uses the provided tools or functions.",
    tools=[may_research_company],
    llm=llm,
    system_prompt="""You are a helpful assistant that researches companies.

CRITICAL: You MUST call the may_research_company function BEFORE providing any information about a company. After calling the function and receiving approval, provide your research summary.""",
)

workflow = AgentWorkflow(
    agents=[agent],
    verbose=True,
)


async def run_until_suspend(company_name: str):
    print("=== RUN #1 (until suspend) ===")

    handler = workflow.run(
        user_msg=f"Please research the company {company_name} and provide a summary."
    )

    ctx_dict = None
    input_event = None

    async for event in handler.stream_events():
        print(f"EVENT TYPE: {type(event).__name__} {event}")

        if isinstance(event, InputRequiredEvent):
            input_event = event
            ctx_dict = handler.ctx.to_dict()
            await handler.cancel_run()
            break

    return ctx_dict, input_event


async def resume_with_response(ctx_dict, human_text: str):
    print("=== RUN #2 (resume) ===")

    restored_ctx = Context.from_dict(workflow, ctx_dict)
    handler = workflow.run(ctx=restored_ctx)

    response_applied = False
    async for event in handler.stream_events():
        print(f"RESUME EVENT TYPE: {type(event).__name__} {event}")
        if isinstance(event, InputRequiredEvent):
            if not response_applied:
                handler.ctx.send_event(HumanResponseEvent(response=human_text))
                response_applied = True
        continue

    result = await handler
    print("\nFinal result:", result)
    return result


async def main():
    # Step 1: run until HITL
    ctx_dict, hitl_event = await run_until_suspend("OpenAI")

    if hitl_event is None:
        print("Error: Workflow completed without emitting InputRequiredEvent")
        return

    # Simulate interactive input
    human_text = input(hitl_event._data.get("prefix") + " ")

    # Step 2: resume from saved context
    await resume_with_response(ctx_dict, human_text)


if __name__ == "__main__":
    asyncio.run(main())
