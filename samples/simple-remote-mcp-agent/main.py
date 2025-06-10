import os

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.llms.openai import OpenAI
from llama_index.tools.mcp import McpToolSpec
from mcp import ClientSession
from mcp.client.sse import sse_client


# Define events
class UserQueryEvent(StartEvent):
    """Event representing a user query to the MCP agent."""

    query: str


class AgentResponseEvent(StopEvent):
    """Event representing the agent's response."""

    response: str


# Define the workflow
class MCPAgentWorkflow(Workflow):
    """Workflow that uses MCP tools to respond to user queries."""

    @step
    async def process_query(self, ev: UserQueryEvent) -> AgentResponseEvent:
        """Process the user query using the MCP-enabled agent."""

        # Initialize MCP client and tools
        async with sse_client(
            url=os.getenv("UIPATH_MCP_SERVER_URL"),
            headers={"Authorization": f"Bearer {os.getenv('UIPATH_ACCESS_TOKEN')}"},
            timeout=60,
        ) as (read, write):
            async with ClientSession(read, write) as client_session:
                await client_session.initialize()
                mcp_tool_spec = McpToolSpec(client=client_session)
                tools = await mcp_tool_spec.to_tool_list_async()

                # Initialize the agent
                self.agent = FunctionAgent(
                    name="UiPath MCP Agent",
                    description="An agent that can interact with MCP tools",
                    llm=OpenAI(model="gpt-4o"),
                    tools=tools,
                    system_prompt="""You are a helpful assistant.
                    You have access to various tools through MCP (Model Context Protocol).
                    Use these tools to help users with their tasks.

                    Always be helpful and provide clear, actionable responses.""",
                )

                response = await self.agent.run(user_msg=ev.query)

        return AgentResponseEvent(response=str(response))


workflow = MCPAgentWorkflow(timeout=300, verbose=True)
