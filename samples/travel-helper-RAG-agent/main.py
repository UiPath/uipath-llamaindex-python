import json
import time

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

from uipath_llamaindex.llms import UiPathOpenAI
from uipath_llamaindex.query_engines import ContextGroundingQueryEngine

index_folder_path = "Shared"
company_policy_index_name = "company_policy"
personal_preferences_index_name = "personal_preferences"
company_policy_files_directory = "sample_data/company_policies"
personal_preferences_files_directory = "sample_data/personal_preferences"

llm = UiPathOpenAI()
uipath = UiPath()


class CustomStartEvent(StartEvent):
    query: str
    add_data_to_index: bool


class QueryEvent(Event):
    pass


class AddDataToIndexEvent(Event):
    pass


class SubQuestionEvent(Event):
    question: str


class WaitForIndexIngestion(Event):
    pass


class OutputEvent(StopEvent):
    """Event representing the final output."""

    output: str


class AnswerEvent(Event):
    question: str
    answer: str


def generate_context_grounding_query_engine_tools(
    response_mode: ResponseMode,
) -> list[QueryEngineTool]:
    response_synthesizer = get_response_synthesizer(
        response_mode=response_mode, llm=llm
    )
    query_engine_policies = ContextGroundingQueryEngine(
        index_name=company_policy_index_name,
        folder_path=index_folder_path,
        response_synthesizer=response_synthesizer,
    )

    query_engine_personal_preferences = ContextGroundingQueryEngine(
        index_name=personal_preferences_index_name,
        folder_path=index_folder_path,
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


async def in_progress_ingestion(index_name: str) -> bool:
    """
    returns True if ingestion finished and was successful, False otherwise
    """
    index = await uipath.context_grounding.retrieve_async(
        index_name, folder_path=index_folder_path
    )
    return index.in_progress_ingestion()


class SubQuestionQueryEngine(Workflow):
    @step
    async def workflow_entrypoint(
        self, ctx: Context, ev: CustomStartEvent
    ) -> QueryEvent | AddDataToIndexEvent:
        await ctx.set("original_query", ev.query)

        if ev.add_data_to_index:
            return AddDataToIndexEvent()
        return QueryEvent()

    @step
    async def add_data_to_index(self, ev: AddDataToIndexEvent) -> WaitForIndexIngestion:
        async def add_file_to_index(file_path, index_name, ingest_data):
            await uipath.context_grounding.add_to_index_async(
                name=index_name,
                folder_path=index_folder_path,
                source_path=file_path,
                blob_file_path=os.path.basename(file_path),
                ingest_data=ingest_data,
            )

        try:
            import os

            company_policy_files = os.listdir(company_policy_files_directory)
            for i in range(len(company_policy_files)):
                ingest_data = i == len(company_policy_files) - 1
                await add_file_to_index(
                    os.path.join(
                        company_policy_files_directory, company_policy_files[i]
                    ),
                    company_policy_index_name,
                    ingest_data,
                )

            personal_preferences_files = os.listdir(
                personal_preferences_files_directory
            )
            for i in range(len(personal_preferences_files)):
                ingest_data = i == len(personal_preferences_files) - 1
                await add_file_to_index(
                    os.path.join(
                        personal_preferences_files_directory,
                        personal_preferences_files[i],
                    ),
                    personal_preferences_index_name,
                    ingest_data,
                )
            return WaitForIndexIngestion()

        except Exception as e:
            print(e)
            raise

    @step
    async def wait_for_index_ingestion(
        self, ev: WaitForIndexIngestion
    ) -> QueryEvent | OutputEvent:
        """
        Since ReAct agents can't handle well 'uipath.models.IngestionInProgressException', we use this node to make sure the data added to indexes was successfully ingested,
        before moving to 'create_sub_questions_plan' step
        """
        no_of_tries = 10
        wait_seconds = 10
        ingested_company_policy_index = ingested_personal_preferences_index = False
        while no_of_tries:
            should_continue = False
            if not ingested_company_policy_index:
                should_continue = True
                ingested_company_policy_index = not await in_progress_ingestion(
                    company_policy_index_name
                )
            if not ingested_personal_preferences_index:
                should_continue = True
                ingested_personal_preferences_index = not await in_progress_ingestion(
                    personal_preferences_index_name
                )
            if not should_continue:
                break
            # wait and retry
            no_of_tries -= 1
            print(
                "Waiting for index ingestion... Retrying "
                + str(no_of_tries)
                + " more time(s)"
            )
            time.sleep(wait_seconds)
        if ingested_company_policy_index and ingested_personal_preferences_index:
            return QueryEvent()
        return OutputEvent(
            output="Cannot evaluate query. Index ingestion is taking too long"
        )

    @step
    async def create_sub_questions_plan(
        self, ctx: Context, ev: QueryEvent
    ) -> SubQuestionEvent:
        query_engine_tools = generate_context_grounding_query_engine_tools(
            response_mode=ResponseMode.SIMPLE_SUMMARIZE
        )

        response = llm.complete(
            f"""
            You are a specialized AI travel recommendation agent working exclusively for corporate travel purposes.
            You have access to the company's allowed travel budget, and optionally, individual employee preference data for their trips.
            Your goal is to provide professional, efficient, and optimized travel recommendations while ensuring compliance with company policies.

            For each request, perform the following:
            1. Summarize the travel information you gathered from the input (destination, dates, employee preferences, company budget, etc.).
            2. Propose an actionable recommendation, such as booking tickets, reservations, or scheduling itineraries, ensuring alignment with the budget and preferences.

            Output relevant sub-questions, such that the answers to all the
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
            ctx.send_event(SubQuestionEvent(question=question))

        return None

    @step
    async def handle_sub_question(self, ev: SubQuestionEvent) -> AnswerEvent:
        print(f"Sub-question is {ev.question}")

        # Recreate tools here instead of retrieving from context
        query_engine_tools = generate_context_grounding_query_engine_tools(
            response_mode=ResponseMode.SIMPLE_SUMMARIZE
        )

        react_agent = ReActAgent.from_tools(query_engine_tools, llm=llm, verbose=True)
        response = react_agent.chat(ev.question)

        return AnswerEvent(question=ev.question, answer=str(response))

    @step
    async def combine_and_interpret_answers(
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


agent = SubQuestionQueryEngine(timeout=120, verbose=True)
