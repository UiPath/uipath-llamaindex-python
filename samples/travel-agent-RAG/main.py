import json

from llama_index.core import get_response_synthesizer
from llama_index.core.agent.react.base import ReActAgent
from llama_index.core.response_synthesizers.type import ResponseMode
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from uipath import UiPath
from uipath.models import ContextGroundingIndex

from uipath_llamaindex.llms import UiPathOpenAI
from uipath_llamaindex.query_engines import ContextGroundingQueryEngine

context_grounding_index_folder_path = "LlamaIndex"
llm = UiPathOpenAI()


class CustomStartEvent(StartEvent):
    query: str


class QueryEvent(Event):
    question: str


class OutputEvent(StopEvent):
    """Event representing the final output."""

    output: str


class AnswerEvent(Event):
    question: str
    answer: str


def generate_context_grounding_query_engine_tools(
    company_policy_index: ContextGroundingIndex,
    personal_preferences_index: ContextGroundingIndex,
    response_mode: ResponseMode,
) -> list[QueryEngineTool]:
    response_synthesizer = get_response_synthesizer(
        response_mode=response_mode, llm=llm
    )
    query_engine_policies = ContextGroundingQueryEngine(
        index_name=company_policy_index.name,
        folder_path=context_grounding_index_folder_path,
        response_synthesizer=response_synthesizer,
    )

    query_engine_personal_preferences = ContextGroundingQueryEngine(
        index_name=personal_preferences_index.name,
        folder_path=context_grounding_index_folder_path,
        response_synthesizer=response_synthesizer,
    )

    return [
        QueryEngineTool(
            query_engine=query_engine_policies,
            metadata=ToolMetadata(
                name="travel_rates_and_company_policy",
                description="Information about company travel rates per states/cities and general company policy",
            ),
        ),
        QueryEngineTool(
            query_engine=query_engine_personal_preferences,
            metadata=ToolMetadata(
                name="personal_preferences",
                description="Information about user's personal preferences",
            ),
        ),
    ]


class SubQuestionQueryEngine(Workflow):
    @step
    async def query(self, ctx: Context, ev: CustomStartEvent) -> QueryEvent:
        uipath = UiPath()
        company_policy_index = uipath.context_grounding.retrieve(
            "company_policy", folder_path=context_grounding_index_folder_path
        )
        personal_preferences_index = uipath.context_grounding.retrieve(
            "personal_preferences", folder_path=context_grounding_index_folder_path
        )
        query_engine_tools = generate_context_grounding_query_engine_tools(
            company_policy_index,
            personal_preferences_index,
            response_mode=ResponseMode.SIMPLE_SUMMARIZE,
        )

        # Store the indices instead of tools
        await ctx.set("company_policy_index", company_policy_index)
        await ctx.set("personal_preferences_index", personal_preferences_index)
        await ctx.set("original_query", ev.query)
        print(f"Query is {await ctx.get('original_query')}")

        response = llm.complete(
            f"""
            You are a specialized AI travel recommendation agent working exclusively for corporate travel purposes. 
            You have access to the company's allowed travel budget, and optionally, individual employee preference data for their trips.
            Your goal is to provide professional, efficient, and optimized travel recommendations while ensuring compliance with company policies.
            
            For each request, perform the following:
            1. Summarize the travel information you gathered from the input (destination, dates, employee preferences, company budget, etc.).
            2. Propose an actionable recommendation, such as booking tickets, reservations, or scheduling itineraries, ensuring alignment with the budget and preferences.
            
            output relevant sub-questions, such that the answers to all the
            sub-questions put together will answer the question. Respond
            in pure JSON without any markdown, like this:
            {{
                "sub_questions": [
                    "What is the allowed expense budget for Amsterdam?",
                    "What are the user's preferences?",
                ]
            }}
            Here is the user query: {await ctx.get("original_query")}

            And here is the list of tools: {query_engine_tools}
            """
        )

        print(f"Sub-questions are {response}")

        response_obj = json.loads(str(response))
        sub_questions = response_obj["sub_questions"]

        await ctx.set("sub_question_count", len(sub_questions))

        for question in sub_questions:
            ctx.send_event(QueryEvent(question=question))

        return None

    @step
    async def sub_question(self, ctx: Context, ev: QueryEvent) -> AnswerEvent:
        print(f"Sub-question is {ev.question}")

        # Recreate tools here instead of retrieving from context
        company_policy_index = await ctx.get("company_policy_index")
        personal_preferences_index = await ctx.get("personal_preferences_index")
        query_engine_tools = generate_context_grounding_query_engine_tools(
            company_policy_index,
            personal_preferences_index,
            response_mode=ResponseMode.SIMPLE_SUMMARIZE,
        )

        agent = ReActAgent.from_tools(query_engine_tools, llm=llm, verbose=True)
        response = agent.chat(ev.question)

        return AnswerEvent(question=ev.question, answer=str(response))

    @step
    async def combine_answers(
        self, ctx: Context, ev: AnswerEvent
    ) -> OutputEvent | None:
        ready = ctx.collect_events(
            ev, [AnswerEvent] * await ctx.get("sub_question_count")
        )
        if ready is None:
            return None

        answers = "\n\n".join(
            [
                f"Question: {event.question}: \n Answer: {event.answer}"
                for event in ready
            ]
        )

        prompt = f"""
            You are given an overall question that has been split into sub-questions,
            each of which has been answered. Combine the answers to all the sub-questions
            into a single answer to the original question.
            Your response should include the following sections:
            ---
            **Travel Summary:**
            - Destination(s): 
            - Travel Dates: 
            - Allowed Budget: 
            - Employee Preferences: 
            
            **Recommendations:**
            - Suggested actions (e.g., purchase tickets for X flights, book accommodations, etc.)
            - Any important notes regarding budget or policy constraints.
            ---
            Be concise yet comprehensive in your response.

            Original query: {await ctx.get("original_query")}

            Sub-questions and answers:
            {answers}
        """

        print(f"Final prompt is {prompt}")

        response = llm.complete(prompt)

        print("Final response is", response)

        return OutputEvent(
            output=response.text,
        )


agent = SubQuestionQueryEngine(timeout=120, verbose=False)
