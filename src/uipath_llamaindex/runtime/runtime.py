"""Runtime class for executing LlamaIndex workflows within the UiPath framework."""

import asyncio
import json
from typing import Any, AsyncGenerator
from uuid import uuid4

from llama_index.core.agent.workflow.workflow_events import (
    AgentInput,
    AgentOutput,
    AgentStream,
    ToolCall,
    ToolCallResult,
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
    UiPathRuntimeStateEvent,
)
from uipath.runtime.schema import UiPathRuntimeSchema
from workflows import Context, Workflow
from workflows.errors import WorkflowTimeoutError
from workflows.events import (
    HumanResponseEvent,
    InputRequiredEvent,
)
from workflows.handler import WorkflowHandler

from uipath_llamaindex.runtime.errors import (
    UiPathLlamaIndexErrorCode,
    UiPathLlamaIndexRuntimeError,
)
from uipath_llamaindex.runtime.schema import get_entrypoints_schema, get_workflow_schema
from uipath_llamaindex.runtime.storage import PickleResumableStorage

from ._serialize import serialize_output


class UiPathLlamaIndexRuntime:
    """
    A runtime class for executing LlamaIndex workflows within the UiPath framework.
    """

    def __init__(
        self,
        workflow: Workflow,
        runtime_id: str | None = None,
        entrypoint: str | None = None,
        storage: PickleResumableStorage | None = None,
    ):
        """
        Initialize the runtime.

        Args:
            workflow: The Workflow to execute
            runtime_id: Unique identifier for this runtime instance
            entrypoint: Optional entrypoint name (for schema generation)
        """
        self.workflow: Workflow = workflow
        self.runtime_id: str = runtime_id or "default"
        self.entrypoint: str | None = entrypoint
        self.storage: PickleResumableStorage | None = storage
        self._context: Context | None = None

    async def execute(
        self,
        input: dict[str, Any] | None = None,
        options: UiPathExecuteOptions | None = None,
    ) -> UiPathRuntimeResult:
        """Execute the workflow with the provided input and configuration."""
        try:
            result: UiPathRuntimeResult | None = None
            async for event in self._run_workflow(input, options, stream_events=False):
                if isinstance(event, UiPathRuntimeResult):
                    result = event

            if result is None:
                raise RuntimeError("Workflow completed without returning a result")

            return result

        except Exception as e:
            raise self._create_runtime_error(e) from e

    async def stream(
        self,
        input: dict[str, Any] | None = None,
        options: UiPathStreamOptions | None = None,
    ) -> AsyncGenerator[UiPathRuntimeEvent, None]:
        """
        Stream workflow execution events in real-time.

        Yields UiPath UiPathRuntimeEvent instances, then yields the final
        UiPathRuntimeResult as the last item.

        Yields:
            - UiPathRuntimeStateEvent: Wraps workflow state updates
            - UiPathRuntimeMessageEvent: Wraps LlamaIndex agent events
            - Final event: UiPathRuntimeResult

        Raises:
            LlamaIndexRuntimeError: If execution fails
        """
        try:
            async for event in self._run_workflow(input, options, stream_events=True):
                yield event
        except Exception as e:
            raise self._create_runtime_error(e) from e

    async def _run_workflow(
        self,
        input: dict[str, Any] | None,
        options: UiPathExecuteOptions | UiPathStreamOptions | None,
        stream_events: bool,
    ) -> AsyncGenerator[UiPathRuntimeEvent | UiPathRuntimeResult, None]:
        """
        Core workflow execution logic used by both execute() and stream().
        """
        workflow_input = input or {}

        is_resuming = options and options.resume

        if not self._context:
            if is_resuming:
                self._context = self._load_context()
            else:
                self._context = Context(self.workflow)

        if is_resuming:
            handler: WorkflowHandler = self.workflow.run(ctx=self._context)
            handler.ctx.send_event(HumanResponseEvent(**workflow_input))
        else:
            start_event_class = self.workflow._start_event_class
            start_event = (
                start_event_class(**workflow_input) if workflow_input else None
            )
            handler = self.workflow.run(start_event=start_event, ctx=self._context)

        event_stream = handler.stream_events()
        suspended_event: InputRequiredEvent | None = None

        is_resumed: bool = False
        async for event in event_stream:
            if stream_events:
                if isinstance(
                    event,
                    (AgentOutput, AgentInput, AgentStream, ToolCall, ToolCallResult),
                ):
                    message_event = UiPathRuntimeMessageEvent(
                        payload=serialize_output(event),
                        node_name=type(event).__name__,
                        execution_id=self.runtime_id,
                    )
                    yield message_event
                else:
                    state_event = UiPathRuntimeStateEvent(
                        payload=serialize_output(event),
                        node_name=type(event).__name__,
                        execution_id=self.runtime_id,
                    )
                    yield state_event

            if isinstance(event, InputRequiredEvent):
                if not is_resumed and is_resuming:
                    is_resumed = True  # First event after resuming
                else:
                    suspended_event = event
                    break

        if suspended_event is not None:
            await asyncio.sleep(0)  # Yield control to event loop
            self._save_context()
            await handler.cancel_run()
            yield self._create_suspended_result(suspended_event)
        else:
            yield self._create_success_result(await handler)

    async def get_schema(self) -> UiPathRuntimeSchema:
        """Get schema for this LlamaIndex runtime."""
        schema_details = get_entrypoints_schema(self.workflow)

        return UiPathRuntimeSchema(
            filePath=self.entrypoint,
            uniqueId=str(uuid4()),
            type="agent",
            input=schema_details.get("input", {}),
            output=schema_details.get("output", {}),
            graph=get_workflow_schema(self.workflow),
        )

    def _create_suspended_result(
        self,
        event: InputRequiredEvent,
    ) -> UiPathRuntimeResult:
        """Create result for suspended execution."""
        if type(event) is InputRequiredEvent:
            prefix: str | None = None
            if hasattr(event, "_data") and "prefix" in event._data:
                prefix = event._data["prefix"]

            return UiPathRuntimeResult(
                output=prefix,
                status=UiPathRuntimeStatus.SUSPENDED,
            )

        return UiPathRuntimeResult(
            output=event,
            status=UiPathRuntimeStatus.SUSPENDED,
        )

    def _create_success_result(self, output: Any) -> UiPathRuntimeResult:
        """Create result for successful completion."""
        if isinstance(output, AgentOutput):
            if output.structured_response is not None:
                serialized_output = serialize_output(output.structured_response)
            else:
                serialized_output = serialize_output(output)
        else:
            serialized_output = serialize_output(output)

        if isinstance(serialized_output, str):
            serialized_output = {"result": serialized_output}

        return UiPathRuntimeResult(
            output=serialized_output,
            status=UiPathRuntimeStatus.SUCCESSFUL,
        )

    def _create_runtime_error(self, e: Exception) -> UiPathLlamaIndexRuntimeError:
        """Handle execution errors and create appropriate LlamaIndexRuntimeError."""
        if isinstance(e, UiPathLlamaIndexRuntimeError):
            return e

        detail = f"Error: {str(e)}"

        if isinstance(e, WorkflowTimeoutError):
            return UiPathLlamaIndexRuntimeError(
                UiPathLlamaIndexErrorCode.TIMEOUT_ERROR,
                "Workflow timed out",
                detail,
                UiPathErrorCategory.USER,
            )

        if isinstance(e, json.JSONDecodeError):
            return UiPathLlamaIndexRuntimeError(
                UiPathErrorCode.INPUT_INVALID_JSON,
                "Invalid JSON input",
                detail,
                UiPathErrorCategory.USER,
            )

        return UiPathLlamaIndexRuntimeError(
            UiPathErrorCode.EXECUTION_ERROR,
            "Workflow execution failed",
            detail,
            UiPathErrorCategory.USER,
        )

    def _load_context(self) -> Context:
        """Load the workflow context from storage."""
        if not self.storage:
            return Context(self.workflow)

        context_dict = self.storage.load_context()

        if context_dict:
            from workflows.context.serializers import JsonPickleSerializer

            serializer = JsonPickleSerializer()
            return Context.from_dict(
                self.workflow,
                context_dict,
                serializer=serializer,
            )
        else:
            return Context(self.workflow)

    def _save_context(self) -> None:
        """Save the current workflow context to storage."""
        if not self.storage or not self._context:
            return None

        from workflows.context.serializers import JsonPickleSerializer

        serializer = JsonPickleSerializer()
        context_dict = self._context.to_dict(serializer=serializer)

        self.storage.save_context(context_dict)

    async def dispose(self) -> None:
        """Cleanup runtime resources."""
        self._context = None
