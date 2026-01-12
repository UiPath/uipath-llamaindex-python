"""Runtime class for executing OpenAI Agents within the UiPath framework."""

import json
import os
from typing import Any, AsyncGenerator
from uuid import uuid4

from agents import (
    Agent,
    Runner,
    SQLiteSession,
)
from uipath.runtime import (
    UiPathExecuteOptions,
    UiPathRuntimeResult,
    UiPathRuntimeStatus,
    UiPathStreamOptions,
)
from uipath.runtime.errors import UiPathErrorCategory, UiPathErrorCode
from uipath.runtime.events import (
    UiPathRuntimeEvent,
    UiPathRuntimeMessageEvent,
)
from uipath.runtime.schema import UiPathRuntimeSchema

from ._serialize import serialize_output
from .errors import UiPathOpenAIAgentsErrorCode, UiPathOpenAIAgentsRuntimeError
from .schema import get_agent_schema, get_entrypoints_schema
from .storage import SqliteAgentStorage


class UiPathOpenAIAgentRuntime:
    """
    A runtime class for executing OpenAI Agents within the UiPath framework.
    """

    def __init__(
        self,
        agent: Agent,
        runtime_id: str | None = None,
        entrypoint: str | None = None,
        storage_path: str | None = None,
        debug_mode: bool = False,
        loaded_object: Any | None = None,
        storage: SqliteAgentStorage | None = None,
    ):
        """
        Initialize the runtime.

        Args:
            agent: The OpenAI Agent to execute
            runtime_id: Unique identifier for this runtime instance
            entrypoint: Optional entrypoint name (for schema generation)
            storage_path: Path to SQLite database for session persistence
            debug_mode: Enable debug mode (not yet implemented)
            loaded_object: Original loaded object (for schema inference)
            storage: Optional storage instance for state persistence
        """
        self.agent: Agent = agent
        self.runtime_id: str = runtime_id or "default"
        self.entrypoint: str | None = entrypoint
        self.storage_path: str | None = storage_path
        self.debug_mode: bool = debug_mode
        self.loaded_object: Any | None = loaded_object
        self.storage: SqliteAgentStorage | None = storage
        self._session: SQLiteSession | None = None

        # Inject UiPath OpenAI client if UiPath credentials are available
        self._setup_uipath_client()

    def _setup_uipath_client(self) -> None:
        """Set up UiPath OpenAI client for agents to use UiPath gateway.

        This injects the UiPath OpenAI client into the OpenAI Agents SDK
        so all agents use the UiPath LLM Gateway instead of direct OpenAI.

        If UiPath credentials are not available, falls back to default OpenAI client.
        """
        try:
            # Import here to avoid circular dependency
            from uipath_openai_agents.chat import UiPathChatOpenAI

            # Check if UiPath credentials are available
            org_id = os.getenv("UIPATH_ORGANIZATION_ID")
            tenant_id = os.getenv("UIPATH_TENANT_ID")
            token = os.getenv("UIPATH_ACCESS_TOKEN")
            uipath_url = os.getenv("UIPATH_URL")

            if org_id and tenant_id and token and uipath_url:
                # Create UiPath OpenAI client
                uipath_client = UiPathChatOpenAI(
                    token=token,
                    org_id=org_id,
                    tenant_id=tenant_id,
                    # Use gpt-4o by default, agents can override via model parameter
                    model_name="gpt-4o",
                )

                # Inject into OpenAI Agents SDK
                # This makes all agents use UiPath gateway
                from agents.models import _openai_shared

                _openai_shared.set_default_openai_client(uipath_client.async_client)

        except ImportError:
            # UiPath chat module not available, skip injection
            pass
        except Exception:
            # If injection fails, fall back to default OpenAI client
            # Agents will use OPENAI_API_KEY if set
            pass

    async def execute(
        self,
        input: dict[str, Any] | None = None,
        options: UiPathExecuteOptions | None = None,
    ) -> UiPathRuntimeResult:
        """
        Execute the agent with the provided input and configuration.

        Args:
            input: Input dictionary containing the message for the agent
            options: Execution options (resume, breakpoints, etc.)

        Returns:
            UiPathRuntimeResult with the agent's output

        Raises:
            UiPathOpenAIAgentRuntimeError: If execution fails
        """
        try:
            result: UiPathRuntimeResult | None = None
            async for event in self._run_agent(input, options, stream_events=False):
                if isinstance(event, UiPathRuntimeResult):
                    result = event

            if result is None:
                raise RuntimeError("Agent completed without returning a result")

            return result

        except Exception as e:
            raise self._create_runtime_error(e) from e

    async def stream(
        self,
        input: dict[str, Any] | None = None,
        options: UiPathStreamOptions | None = None,
    ) -> AsyncGenerator[UiPathRuntimeEvent, None]:
        """
        Stream agent execution events in real-time.

        Args:
            input: Input dictionary containing the message for the agent
            options: Stream options

        Yields:
            UiPathRuntimeEvent instances during execution,
            then the final UiPathRuntimeResult

        Raises:
            UiPathOpenAIAgentRuntimeError: If execution fails
        """
        try:
            async for event in self._run_agent(input, options, stream_events=True):
                yield event
        except Exception as e:
            raise self._create_runtime_error(e) from e

    async def _run_agent(
        self,
        input: dict[str, Any] | None,
        options: UiPathExecuteOptions | UiPathStreamOptions | None,
        stream_events: bool,
    ) -> AsyncGenerator[UiPathRuntimeEvent | UiPathRuntimeResult, None]:
        """
        Core agent execution logic used by both execute() and stream().

        Args:
            input: Input dictionary
            options: Execution/stream options
            stream_events: Whether to stream events during execution

        Yields:
            Runtime events if stream_events=True, then final result
        """
        agent_input = self._prepare_agent_input(input)
        is_resuming = bool(options and options.resume)

        # Get or create session for state persistence
        # SQLiteSession automatically loads existing data from the database when created
        if self.storage_path:
            self._session = SQLiteSession(self.runtime_id, self.storage_path)
        else:
            self._session = None

        # Run the agent
        try:
            # OpenAI Agents Runner.run() is async and returns a RunResult
            # Note: starting_agent is the first positional parameter
            result = await Runner.run(
                starting_agent=self.agent,
                input=agent_input,
                session=self._session,
            )

            # Stream events if requested
            if stream_events and hasattr(result, "messages"):
                # Emit message events for each message in the conversation
                for message in result.messages:
                    message_event = UiPathRuntimeMessageEvent(
                        payload=self._serialize_message(message),
                        node_name=getattr(self.agent, "name", "agent"),
                        execution_id=self.runtime_id,
                    )
                    yield message_event

            # SQLiteSession automatically persists data when items are added
            # No explicit save() needed

            # Yield final result
            yield self._create_success_result(result.final_output)

        except Exception:
            # Clean up session on error
            if self._session and self.storage_path and not is_resuming:
                # Delete incomplete session
                try:
                    import os

                    if os.path.exists(self.storage_path):
                        os.remove(self.storage_path)
                except Exception:
                    pass  # Best effort cleanup
            raise

    def _prepare_agent_input(self, input: dict[str, Any] | None) -> str | list:
        """
        Prepare agent input from UiPath input dictionary.

        Supports two input formats:
        - {"message": "text"} → returns string for Runner.run()
        - {"messages": [...]} → returns list of message dicts for Runner.run()

        Note: When using sessions, string input is preferred as it doesn't
        require a session_input_callback.

        Args:
            input: Input dictionary from UiPath

        Returns:
            String or list for Runner.run() input parameter

        Raises:
            ValueError: If input doesn't contain "message" or "messages" field
        """
        if not input:
            raise ValueError(
                "Input is required. Provide either 'message' (string) or 'messages' (list of message dicts)"
            )

        # Check for "messages" field (list of message dicts)
        if "messages" in input:
            messages = input["messages"]
            # Ensure it's a list
            if isinstance(messages, list):
                return messages
            else:
                raise ValueError(
                    "'messages' field must be a list of message dictionaries"
                )

        # Check for "message" field (simple string)
        if "message" in input:
            message = input["message"]
            # Return as string (OpenAI Agents SDK handles string → message conversion)
            return str(message)

        # No valid field found
        raise ValueError(
            "Input must contain either 'message' (string) or 'messages' (list of message dicts). "
            f"Got keys: {list(input.keys())}"
        )

    def _serialize_message(self, message: Any) -> dict[str, Any]:
        """
        Serialize an agent message for event streaming.

        Args:
            message: Message object from the agent

        Returns:
            Dictionary representation of the message
        """
        serialized = serialize_output(message)

        # Ensure the result is a dictionary
        if isinstance(serialized, dict):
            return serialized

        # Fallback to wrapping in a content field
        return {"content": serialized}

    def _create_success_result(self, output: Any) -> UiPathRuntimeResult:
        """
        Create result for successful completion.

        Args:
            output: The agent's output

        Returns:
            UiPathRuntimeResult with serialized output
        """
        # Serialize output
        serialized_output = self._serialize_output(output)

        # Ensure output is a dictionary
        if not isinstance(serialized_output, dict):
            serialized_output = {"result": serialized_output}

        return UiPathRuntimeResult(
            output=serialized_output,
            status=UiPathRuntimeStatus.SUCCESSFUL,
        )

    def _serialize_output(self, output: Any) -> Any:
        """
        Serialize agent output to a JSON-compatible format.

        Args:
            output: Output from the agent

        Returns:
            JSON-compatible representation
        """
        return serialize_output(output)

    def _create_runtime_error(self, e: Exception) -> UiPathOpenAIAgentsRuntimeError:
        """
        Handle execution errors and create appropriate runtime error.

        Args:
            e: The exception that occurred

        Returns:
            UiPathOpenAIAgentsRuntimeError with appropriate error code
        """
        if isinstance(e, UiPathOpenAIAgentsRuntimeError):
            return e

        detail = f"Error: {str(e)}"

        if isinstance(e, json.JSONDecodeError):
            return UiPathOpenAIAgentsRuntimeError(
                UiPathErrorCode.INPUT_INVALID_JSON,
                "Invalid JSON input",
                detail,
                UiPathErrorCategory.USER,
            )

        if isinstance(e, TimeoutError):
            return UiPathOpenAIAgentsRuntimeError(
                UiPathOpenAIAgentsErrorCode.TIMEOUT_ERROR,
                "Agent execution timed out",
                detail,
                UiPathErrorCategory.USER,
            )

        return UiPathOpenAIAgentsRuntimeError(
            UiPathOpenAIAgentsErrorCode.AGENT_EXECUTION_FAILURE,
            "Agent execution failed",
            detail,
            UiPathErrorCategory.USER,
        )

    async def get_schema(self) -> UiPathRuntimeSchema:
        """
        Get schema for this OpenAI Agent runtime.

        Returns:
            UiPathRuntimeSchema with input/output schemas and graph structure
        """
        entrypoints_schema = get_entrypoints_schema(self.agent, self.loaded_object)

        return UiPathRuntimeSchema(
            filePath=self.entrypoint,
            uniqueId=str(uuid4()),
            type="agent",
            input=entrypoints_schema.get("input", {}),
            output=entrypoints_schema.get("output", {}),
            graph=get_agent_schema(self.agent),
        )

    async def dispose(self) -> None:
        """Cleanup runtime resources."""
        # Clean up storage first (before event loop closes)
        if self.storage:
            try:
                await self.storage.dispose()
            except Exception:
                pass  # Best effort cleanup

        self._session = None
        self.storage = None
