"""Runtime class for executing OpenAI Agents within the UiPath framework."""

import json
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

from .schema import get_agent_schema, get_entrypoints_schema


class UiPathOpenAIAgentRuntimeError(Exception):
    """Custom exception for OpenAI Agent runtime errors."""

    def __init__(
        self,
        code: str,
        message: str,
        detail: str | None = None,
        category: UiPathErrorCategory = UiPathErrorCategory.USER,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.category = category
        super().__init__(f"{code}: {message}")


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
    ):
        """
        Initialize the runtime.

        Args:
            agent: The OpenAI Agent to execute
            runtime_id: Unique identifier for this runtime instance
            entrypoint: Optional entrypoint name (for schema generation)
            storage_path: Path to SQLite database for session persistence
            debug_mode: Enable debug mode (not yet implemented)
        """
        self.agent: Agent = agent
        self.runtime_id: str = runtime_id or "default"
        self.entrypoint: str | None = entrypoint
        self.storage_path: str | None = storage_path
        self.debug_mode: bool = debug_mode
        self._session: SQLiteSession | None = None

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

    def _prepare_agent_input(self, input: dict[str, Any] | None) -> Any:
        """
        Prepare agent input from UiPath input dictionary.

        Args:
            input: Input dictionary from UiPath

        Returns:
            Formatted input for the agent (string or list of messages)
        """
        if not input:
            return ""

        # Extract message from input
        message = input.get("message")

        if not message:
            # If no message field, treat entire input as message
            return input

        # Return message as-is (string or list of messages)
        return message

    def _serialize_message(self, message: Any) -> dict[str, Any]:
        """
        Serialize an agent message for event streaming.

        Args:
            message: Message object from the agent

        Returns:
            Dictionary representation of the message
        """
        if isinstance(message, dict):
            return message

        # Try to convert message to dict
        if hasattr(message, "model_dump"):
            return message.model_dump()
        if hasattr(message, "dict"):
            return message.dict()
        if hasattr(message, "__dict__"):
            return message.__dict__

        # Fallback to string representation
        return {"content": str(message)}

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
        if output is None:
            return None

        # Handle Pydantic models
        if hasattr(output, "model_dump"):
            return output.model_dump()
        if hasattr(output, "dict"):
            return output.dict()

        # Handle common types
        if isinstance(output, (str, int, float, bool, list, dict)):
            return output

        # Handle dataclasses
        if hasattr(output, "__dataclass_fields__"):
            from dataclasses import asdict

            return asdict(output)

        # Try JSON serialization
        try:
            json.dumps(output)
            return output
        except (TypeError, ValueError):
            pass

        # Fallback to string representation
        return str(output)

    def _create_runtime_error(self, e: Exception) -> UiPathOpenAIAgentRuntimeError:
        """
        Handle execution errors and create appropriate runtime error.

        Args:
            e: The exception that occurred

        Returns:
            UiPathOpenAIAgentRuntimeError with appropriate error code
        """
        if isinstance(e, UiPathOpenAIAgentRuntimeError):
            return e

        detail = f"Error: {str(e)}"

        if isinstance(e, json.JSONDecodeError):
            return UiPathOpenAIAgentRuntimeError(
                UiPathErrorCode.INPUT_INVALID_JSON,
                "Invalid JSON input",
                detail,
                UiPathErrorCategory.USER,
            )

        if isinstance(e, TimeoutError):
            return UiPathOpenAIAgentRuntimeError(
                UiPathErrorCode.EXECUTION_ERROR,
                "Agent execution timed out",
                detail,
                UiPathErrorCategory.USER,
            )

        return UiPathOpenAIAgentRuntimeError(
            UiPathErrorCode.EXECUTION_ERROR,
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
        entrypoints_schema = get_entrypoints_schema(self.agent)

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
        self._session = None
