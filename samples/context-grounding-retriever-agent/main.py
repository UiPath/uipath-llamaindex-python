import time
from datetime import datetime, timedelta

from langchain_community.tools.tavily_search import TavilySearchResults
from llama_index.core import get_response_synthesizer
from llama_index.core.agent import ReActAgent
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

INDEX_NAME = "News-Index"
FOLDER_PATH = "Shared"
FRESHNESS_HOURS = 24

uipath = UiPath()
tavily_tool = TavilySearchResults(max_results=5)


class CheckIndexEvent(Event):
    topic: str


class SearchWebEvent(Event):
    topic: str


class AddToIndexEvent(Event):
    topic: str
    web_results: str


class WaitForIngestionEvent(Event):
    pass


class QueryIndexEvent(Event):
    topic: str


async def check_index_freshness(topic: str) -> bool:
    try:
        index = await uipath.context_grounding.retrieve_async(
            INDEX_NAME, folder_path=FOLDER_PATH
        )

        if index.last_ingested is None:
            print("Index has never been ingested")
            return False

        last_ingested_time = index.last_ingested
        current_time = datetime.now(last_ingested_time.tzinfo)
        time_diff = current_time - last_ingested_time

        print(f"Last ingested: {last_ingested_time}")
        print(f"Time since last ingestion: {time_diff}")

        if time_diff < timedelta(hours=FRESHNESS_HOURS):
            print(f"Data is fresh (less than {FRESHNESS_HOURS} hours old)")
            return True
        else:
            print(f"Data is stale (more than {FRESHNESS_HOURS} hours old)")
            return False
    except Exception:
        return False


async def in_progress_ingestion() -> bool:
    try:
        index = await uipath.context_grounding.retrieve_async(
            INDEX_NAME, folder_path=FOLDER_PATH
        )
        status = index.last_ingestion_status
        return status in ["Queued", "InProgress", "Running"]
    except Exception:
        return False


class NewsAggregatorWorkflow(Workflow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = UiPathOpenAI(model="gpt-4o-2024-11-20")

    @step
    async def start(self, ctx: Context, ev: StartEvent) -> CheckIndexEvent:
        query = ev.get("query", "")

        if not query:
            return StopEvent(result="No query provided")

        await ctx.store.set("original_query", query)

        topic_response = await self.llm.acomplete(
            f"Extract the main topic/subject from this query. Return only the topic name, nothing else: {query}"
        )
        topic = str(topic_response).strip()
        await ctx.store.set("topic", topic)

        return CheckIndexEvent(topic=topic)

    @step
    async def check_index(
        self, ctx: Context, ev: CheckIndexEvent
    ) -> SearchWebEvent | QueryIndexEvent:
        has_fresh_data = await check_index_freshness(ev.topic)

        if has_fresh_data:
            print(f"Found fresh data about {ev.topic} in index")
            return QueryIndexEvent(topic=ev.topic)
        else:
            print(f"No fresh data found, searching web for {ev.topic}")
            return SearchWebEvent(topic=ev.topic)

    @step
    async def search_web(self, ctx: Context, ev: SearchWebEvent) -> AddToIndexEvent:
        print(f"Searching web for: {ev.topic}")

        results = tavily_tool.invoke({"query": f"latest news about {ev.topic}"})

        formatted_results = (
            f"News about {ev.topic} (Retrieved: {datetime.now().isoformat()})\n\n"
        )
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. {result.get('content', '')}\n"
            formatted_results += f"   Source: {result.get('url', 'N/A')}\n\n"

        print(f"Found {len(results)} results")
        return AddToIndexEvent(topic=ev.topic, web_results=formatted_results)

    @step
    async def add_to_index(
        self, ctx: Context, ev: AddToIndexEvent
    ) -> WaitForIngestionEvent:
        timestamp = int(time.time())
        file_name_response = await self.llm.acomplete(
            f"""Generate a file name from this topic, replacing spaces with underscores.
            For instance, 'Tesla news' should be 'tesla_news'.
            Topic: {ev.topic}
            Return only the filename without extension."""
        )
        file_name = str(file_name_response).strip().replace(" ", "_")

        print(f"Adding data to index with filename: {file_name}-{timestamp}.txt")
        await uipath.context_grounding.add_to_index_async(
            name=INDEX_NAME,
            blob_file_path=f"{file_name}-{timestamp}.txt",
            content_type="application/txt",
            content=ev.web_results,
            folder_path=FOLDER_PATH,
        )

        return WaitForIngestionEvent()

    @step
    async def wait_for_ingestion(
        self, ctx: Context, ev: WaitForIngestionEvent
    ) -> QueryIndexEvent | StopEvent:
        no_of_tries = 10
        wait_seconds = 5

        while no_of_tries > 0:
            if not await in_progress_ingestion():
                print("Ingestion complete!")
                topic = await ctx.store.get("topic")
                return QueryIndexEvent(topic=topic)

            no_of_tries -= 1
            print(f"Waiting for ingestion... Retrying {no_of_tries} more time(s)")
            time.sleep(wait_seconds)

        return StopEvent(
            result="Index ingestion took too long. Please try again later."
        )

    @step
    async def query_index(self, ctx: Context, ev: QueryIndexEvent) -> StopEvent:
        print(f"Querying index for: {ev.topic}")

        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.SIMPLE_SUMMARIZE, llm=self.llm
        )

        query_engine = ContextGroundingQueryEngine(
            index_name=INDEX_NAME,
            folder_path=FOLDER_PATH,
            response_synthesizer=response_synthesizer,
        )

        tool = QueryEngineTool(
            query_engine=query_engine,
            metadata=ToolMetadata(
                name="news_search",
                description=f"Search through indexed news articles about {ev.topic}",
            ),
        )

        agent = ReActAgent(tools=[tool], llm=self.llm, verbose=True)
        original_query = await ctx.store.get("original_query")
        response = await agent.run(user_msg=original_query)

        return StopEvent(result=str(response))


agent = NewsAggregatorWorkflow(timeout=180, verbose=True)
