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
from uipath.runtime.debug import UiPathBreakpointResult
from uipath.runtime.errors import UiPathErrorCategory, UiPathErrorCode
from uipath.runtime.events import (
    UiPathRuntimeEvent,
    UiPathRuntimeMessageEvent,
    UiPathRuntimeStateEvent,
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

        # Configure OpenAI Agents SDK to use Responses API
        # UiPath supports both APIs via X-UiPath-LlmGateway-ApiFlavor header
        # Using responses API for enhanced agent capabilities (conversation state, reasoning)
        from agents import set_default_openai_api

        set_default_openai_api("responses")

        # Inject UiPath OpenAI client if UiPath credentials are available
        self._setup_uipath_client()

    def _setup_uipath_client(self) -> None:
        """Set up UiPath OpenAI client for agents to use UiPath gateway.

        This injects the UiPath OpenAI client into the OpenAI Agents SDK
        so all agents use the UiPath LLM Gateway instead of direct OpenAI.

        The model is automatically extracted from the agent's `model` parameter.
        If not specified in Agent(), the SDK uses agents.models.get_default_model().

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
                # Extract model from agent definition
                from agents.models import get_default_model

                from uipath_openai_agents.chat.supported_models import OpenAIModels

                if hasattr(self.agent, "model") and self.agent.model:
                    model_name = str(self.agent.model)
                else:
                    model_name = get_default_model()

                # Normalize generic model names to UiPath-specific versions
                model_name = OpenAIModels.normalize_model_name(model_name)

                # Create UiPath OpenAI client
                uipath_client = UiPathChatOpenAI(
                    token=token,
                    org_id=org_id,
                    tenant_id=tenant_id,
                    model_name=model_name,
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

        # Determine if breakpoints are enabled
        has_breakpoints = (
            options and hasattr(options, "breakpoints") and options.breakpoints
        )

        # Run the agent with streaming if events or breakpoints requested
        try:
            if stream_events or has_breakpoints:
                # Use streaming for events and breakpoint support
                async for event_or_result in self._run_agent_streamed(
                    agent_input, options, stream_events
                ):
                    yield event_or_result
            else:
                # Use non-streaming for simple execution
                result = await Runner.run(
                    starting_agent=self.agent,
                    input=agent_input,
                    session=self._session,
                )
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

    async def _run_agent_streamed(
        self,
        agent_input: str | list[Any],
        options: UiPathExecuteOptions | UiPathStreamOptions | None,
        stream_events: bool,
    ) -> AsyncGenerator[UiPathRuntimeEvent | UiPathRuntimeResult, None]:
        """
        Run agent using streaming API to enable breakpoints and event streaming.

        Args:
            agent_input: Prepared agent input (string or list of messages)
            options: Execution/stream options. Can include:
                - breakpoints: List of breakpoint names or "*" for all
                - resume_event: asyncio.Event to signal resume from breakpoints
            stream_events: Whether to yield streaming events to caller

        Yields:
            Runtime events if stream_events=True, breakpoint results, then final result
        """

        # Get breakpoints configuration
        breakpoints = None
        resume_event = None
        if options:
            if hasattr(options, "breakpoints"):
                breakpoints = options.breakpoints
            # Get resume event if provided (uses extra="allow" from Pydantic)
            if hasattr(options, "resume_event"):
                resume_event = getattr(options, "resume_event", None)

        # Use Runner.run_streamed() for streaming events (returns RunResultStreaming directly)
        result = Runner.run_streamed(
            starting_agent=self.agent,
            input=agent_input,
            session=self._session,
        )

        # Stream events from the agent
        async for event in result.stream_events():
            # Check if this event should trigger a breakpoint
            should_pause = self._should_pause_at_event(event, breakpoints)

            if should_pause:
                # Hit a breakpoint - pause execution
                # Create and yield breakpoint result
                breakpoint_result = self._create_breakpoint_result_from_event(event)
                yield breakpoint_result

                # Wait for resume signal if provided
                if resume_event is not None:
                    # Clear the event first to ensure we wait for new signal
                    resume_event.clear()
                    # Wait for external debugger to signal resume
                    await resume_event.wait()
                # If no resume_event provided, auto-resume immediately

            # Emit the event to caller if streaming is enabled
            if stream_events:
                runtime_event = self._convert_stream_event_to_runtime_event(event)
                if runtime_event:
                    yield runtime_event

        # Stream complete - yield final result
        yield self._create_success_result(result.final_output)

    def _should_pause_at_event(
        self,
        event: Any,
        breakpoints: list[str] | str | None,
    ) -> bool:
        """
        Determine if execution should pause at this streaming event.

        Matches behavior of LangChain (interrupt_before) and LlamaIndex (step name filtering)
        by supporting specific tool and agent names only.

        Args:
            event: Streaming event from Runner.run_streamed()
            breakpoints: List of specific names to break on. Can be:
                - "*": Pause on all significant events (special case)
                - ["calculate_sum"]: Pause only when calculate_sum tool is called
                - ["french_agent"]: Pause only when handing off to french_agent
                - ["calculate_sum", "french_agent", "get_weather"]: Pause on any of these

        Returns:
            True if should pause, False otherwise
        """
        if not breakpoints:
            return False

        # Get event type/name
        event_type = getattr(event, "type", None)
        event_name = getattr(event, "name", None)

        # Pause on all events
        if breakpoints == "*":
            # Only pause on significant events, not raw response deltas
            if event_type == "run_item_stream_event":
                return event_name in [
                    "tool_called",
                    "handoff_requested",
                    "mcp_approval_requested",
                ]
            return False

        # Check if event matches configured breakpoints (by name only, like LangChain/LlamaIndex)
        if isinstance(breakpoints, list):
            for bp in breakpoints:
                # Check for specific tool name match (when event is tool_called)
                if (
                    event_name == "tool_called"
                    and event_type == "run_item_stream_event"
                ):
                    event_item = getattr(event, "item", None)
                    if event_item:
                        # Extract tool name from the event
                        tool_name = getattr(event_item, "name", None)
                        if tool_name and tool_name == bp:
                            return True

                # Check for specific agent name match (when event is handoff_requested)
                if (
                    event_name == "handoff_requested"
                    and event_type == "run_item_stream_event"
                ):
                    event_item = getattr(event, "item", None)
                    if event_item:
                        # Extract target agent name from the handoff event
                        target_agent = getattr(event_item, "target_agent", None)
                        if target_agent:
                            agent_name = getattr(target_agent, "name", None)
                            if agent_name and agent_name == bp:
                                return True

        return False

    def _create_breakpoint_result_from_event(
        self,
        event: Any,
    ) -> UiPathBreakpointResult:
        """
        Create a breakpoint result from a streaming event.

        Args:
            event: The streaming event that triggered the breakpoint

        Returns:
            UiPathBreakpointResult for this breakpoint
        """
        event_name = getattr(event, "name", "unknown")
        event_item = getattr(event, "item", None)

        # Serialize event state
        current_state = serialize_output(event_item) if event_item else {}

        return UiPathBreakpointResult(
            breakpoint_node=event_name,
            breakpoint_type="before",
            current_state=current_state,
            next_nodes=[],  # Not available in streaming context
        )

    def _convert_stream_event_to_runtime_event(
        self,
        event: Any,
    ) -> UiPathRuntimeEvent | None:
        """
        Convert OpenAI streaming event to UiPath runtime event.

        Args:
            event: Streaming event from Runner.run_streamed()

        Returns:
            UiPathRuntimeEvent or None if event should be filtered
        """

        event_type = getattr(event, "type", None)
        event_name = getattr(event, "name", None)

        # Handle run item events (messages, tool calls, etc.)
        if event_type == "run_item_stream_event":
            event_item = getattr(event, "item", None)
            if event_item:
                # Determine if this is a message or state event
                if event_name in ["message_output_created", "reasoning_item_created"]:
                    return UiPathRuntimeMessageEvent(
                        payload=serialize_output(event_item),
                        metadata={"event_name": event_name},
                    )
                else:
                    return UiPathRuntimeStateEvent(
                        payload=serialize_output(event_item),
                        metadata={"event_name": event_name},
                    )

        # Handle agent updated events
        if event_type == "agent_updated_stream_event":
            new_agent = getattr(event, "new_agent", None)
            if new_agent:
                return UiPathRuntimeStateEvent(
                    payload={"agent_name": getattr(new_agent, "name", "unknown")},
                    metadata={"event_type": "agent_updated"},
                )

        # Filter out raw response events (too granular)
        return None

    def _prepare_agent_input(self, input: dict[str, Any] | None) -> str | list[Any]:
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
        # Storage is shared across runtimes and managed by the factory
        # Do not dispose it here
        pass
