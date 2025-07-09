import json
import logging
import os
import pickle
from contextlib import suppress
from typing import Optional, cast

from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
    JsonPickleSerializer,
    WorkflowTimeoutError,
)
from llama_index.core.workflow.handler import WorkflowHandler  # type: ignore
from openinference.instrumentation.llama_index import (
    LlamaIndexInstrumentor,
    get_current_span,
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from uipath._cli._runtime._contracts import (
    UiPathBaseRuntime,
    UiPathErrorCategory,
    UiPathResumeTrigger,
    UiPathRuntimeResult,
    UiPathRuntimeStatus,
)
from uipath._cli._runtime._hitl import HitlProcessor, HitlReader
from uipath.tracing import TracingManager

from .._tracing._oteladapter import LlamaIndexExporter
from ._context import UiPathLlamaIndexRuntimeContext
from ._exception import UiPathLlamaIndexRuntimeError

logger = logging.getLogger(__name__)


class UiPathLlamaIndexRuntime(UiPathBaseRuntime):
    """
    A runtime class for hosting UiPath LlamaIndex agents.
    """

    def __init__(self, context: UiPathLlamaIndexRuntimeContext):
        super().__init__(context)
        self.context: UiPathLlamaIndexRuntimeContext = context

    async def execute(self) -> Optional[UiPathRuntimeResult]:
        """
        Start the LlamaIndex agent runtime.

        Returns:
            Dictionary with execution results

        Raises:
            UiPathLlamaIndexRuntimeError: If execution fails
        """
        await self.validate()

        self.trace_provider = TracerProvider()
        self.tracer = self.trace_provider.get_tracer("uipath.llamaindex.runtime")

        with suppress(Exception):
            trace.set_tracer_provider(self.trace_provider)
            self.trace_provider.add_span_processor(
                BatchSpanProcessor(LlamaIndexExporter())
            )

            LlamaIndexInstrumentor().instrument(tracer_provider=self.trace_provider)

            TracingManager.register_current_span_provider(get_current_span)

        try:
            if self.context.resume is False and self.context.job_id is None:
                # Delete the previous graph state file at debug time
                if os.path.exists(self.state_file_path):
                    os.remove(self.state_file_path)

            if self.context.workflow is None:
                return None

            start_event_class = self.context.workflow._start_event_class
            ev = start_event_class(**(self.context.input_json or {}))
            await self.load_workflow_context()

            if self.context.workflow_context is None:
                return None

            handler: WorkflowHandler = self.context.workflow.run(
                start_event=ev if self.context.resume else None,
                ctx=self.context.workflow_context,
                **(self.context.input_json or {}),
            )

            resume_trigger: Optional[UiPathResumeTrigger] = None

            response_applied = False
            async for event in handler.stream_events():
                # log the received event on trace level
                if isinstance(event, InputRequiredEvent):
                    # for api trigger hitl scenarios only pass the str input for processing
                    hitl_processor = HitlProcessor(value=event.prefix)
                    if self.context.resume and not response_applied:
                        # If we are resuming, we need to apply the response to the event stream.
                        response_applied = True
                        response_event = await self.get_response_event()
                        if response_event:
                            # If we have a response event, send it to the workflow context.
                            self.context.workflow_context.send_event(response_event)
                    else:
                        resume_trigger = await hitl_processor.create_resume_trigger()
                        break

            if resume_trigger is None:
                try:
                    output = await handler
                # catch any script exceptions
                except Exception as e:
                    raise UiPathLlamaIndexRuntimeError(
                        "AGENT_EXECUTION_FAILURE",
                        "There was an exception while executing the agent ",
                        str(e),
                        UiPathErrorCategory.USER,
                    ) from e
                try:
                    serialized_output = self._serialize_object(output)
                    # create simple kvp from string
                    if type(serialized_output) is str:
                        serialized_output = {"result": serialized_output}

                    print(serialized_output)
                    self.context.result = UiPathRuntimeResult(
                        output=serialized_output,
                        status=UiPathRuntimeStatus.SUCCESSFUL,
                    )
                # check if workflow failed because of timeout constraints
                except WorkflowTimeoutError as e:
                    raise UiPathLlamaIndexRuntimeError(
                        "TIMEOUT_ERROR",
                        "Workflow timed out",
                        str(e),
                        UiPathErrorCategory.USER,
                    ) from e
                except Exception as e:
                    raise UiPathLlamaIndexRuntimeError(
                        "SERIALIZE_OUTPUT_ERROR",
                        "Failed to serialize output",
                        str(e),
                        UiPathErrorCategory.SYSTEM,
                    ) from e
            else:
                self.context.result = UiPathRuntimeResult(
                    status=UiPathRuntimeStatus.SUSPENDED,
                    resume=resume_trigger,
                )

            if self.state_file_path:
                serializer = JsonPickleSerializer()
                ctx_dict = self.context.workflow_context.to_dict(serializer=serializer)
                ctx_dict["uipath_resume_trigger"] = (
                    serializer.serialize(resume_trigger) if resume_trigger else None
                )
                with open(self.state_file_path, "wb") as f:
                    pickle.dump(ctx_dict, f)

            return self.context.result

        except Exception as e:
            if isinstance(e, UiPathLlamaIndexRuntimeError):
                raise
            detail = f"Error: {str(e)}"
            raise UiPathLlamaIndexRuntimeError(
                "EXECUTION_ERROR",
                "LlamaIndex Runtime execution failed",
                detail,
                UiPathErrorCategory.USER,
            ) from e
        finally:
            self.trace_provider.shutdown()

    async def validate(self) -> None:
        """Validate runtime inputs and load Llama agent configuration."""
        try:
            if self.context.input:
                self.context.input_json = json.loads(self.context.input)
        except json.JSONDecodeError as e:
            raise UiPathLlamaIndexRuntimeError(
                "INPUT_INVALID_JSON",
                "Invalid JSON input",
                "The input data is not valid JSON.",
                UiPathErrorCategory.USER,
            ) from e

        if self.context.config is None:
            raise UiPathLlamaIndexRuntimeError(
                "CONFIG_MISSING",
                "Invalid configuration",
                "Failed to load configuration",
                UiPathErrorCategory.DEPLOYMENT,
            )

        try:
            self.context.config.load_config()
        except Exception as e:
            raise UiPathLlamaIndexRuntimeError(
                "CONFIG_INVALID",
                "Invalid configuration",
                f"Failed to load configuration: {str(e)}",
                UiPathErrorCategory.DEPLOYMENT,
            ) from e

        # Determine entrypoint if not provided
        workflows = self.context.config.workflows
        if not self.context.entrypoint and len(workflows) == 1:
            self.context.entrypoint = workflows[0].name
        elif not self.context.entrypoint:
            workflow_names = ", ".join(w.name for w in workflows)
            raise UiPathLlamaIndexRuntimeError(
                "ENTRYPOINT_MISSING",
                "Entrypoint required",
                f"Multiple workflows available. Please specify one of: {workflow_names}.",
                UiPathErrorCategory.DEPLOYMENT,
            )

        # Get the specified workflow configuration
        self.workflow_config = self.context.config.get_workflow(self.context.entrypoint)
        if not self.workflow_config:
            raise UiPathLlamaIndexRuntimeError(
                "WORKFLOW_NOT_FOUND",
                "Workflow not found",
                f"Workflow '{self.context.entrypoint}' not found.",
                UiPathErrorCategory.DEPLOYMENT,
            )
        try:
            self.context.workflow = await self.workflow_config.load_workflow()
        except ImportError as e:
            raise UiPathLlamaIndexRuntimeError(
                "WORKFLOW_IMPORT_ERROR",
                "Workflow import failed",
                f"Failed to import workflow '{self.context.entrypoint}': {str(e)}",
                UiPathErrorCategory.USER,
            ) from e
        except TypeError as e:
            raise UiPathLlamaIndexRuntimeError(
                "WORKFLOW_TYPE_ERROR",
                "Invalid workflow type",
                f"Workflow '{self.context.entrypoint}' is not a valid `Workflow`: {str(e)}",
                UiPathErrorCategory.USER,
            ) from e
        except ValueError as e:
            raise UiPathLlamaIndexRuntimeError(
                "WORKFLOW_VALUE_ERROR",
                "Invalid workflow value",
                f"Invalid value in workflow '{self.context.entrypoint}': {str(e)}",
                UiPathErrorCategory.USER,
            ) from e
        except Exception as e:
            raise UiPathLlamaIndexRuntimeError(
                "WORKFLOW_LOAD_ERROR",
                "Failed to load workflow",
                f"Unexpected error loading workflow '{self.context.entrypoint}': {str(e)}",
                UiPathErrorCategory.USER,
            ) from e

    async def cleanup(self) -> None:
        """Clean up all resources."""
        pass

    async def load_workflow_context(self):
        """
        Load the workflow context for the LlamaIndex agent.
        """
        logger.debug(f"Resumed: {self.context.resume} Input: {self.context.input_json}")

        if self.context.workflow is None:
            return

        if not self.context.resume:
            self.context.workflow_context = Context(self.context.workflow)
            return

        if not self.state_file_path or not os.path.exists(self.state_file_path):
            self.context.workflow_context = Context(self.context.workflow)
            return

        serializer = JsonPickleSerializer()

        with open(self.state_file_path, "rb") as f:
            loaded_ctx_dict = pickle.load(f)
            self.context.workflow_context = Context.from_dict(
                self.context.workflow,
                loaded_ctx_dict,
                serializer=serializer,
            )
            # TODO check multiple HITL same agent
            resumed_trigger_data = loaded_ctx_dict["uipath_resume_trigger"]
            if resumed_trigger_data:
                self.context.resumed_trigger = cast(
                    UiPathResumeTrigger, serializer.deserialize(resumed_trigger_data)
                )

    async def get_response_event(self) -> Optional[HumanResponseEvent]:
        """
        Get the response event for the LlamaIndex agent.

        Returns:
            The response event if available, otherwise None.
        """
        if self.context.input_json:
            # If input_json is provided, use it to create a HumanResponseEvent
            return HumanResponseEvent(**(self.context.input_json or {}))
        # If resumed_trigger is set, fetch the feedback
        if self.context.resumed_trigger:
            feedback = await HitlReader.read(self.context.resumed_trigger)
            if feedback:
                if isinstance(feedback, dict):
                    feedback = json.dumps(feedback)
                elif isinstance(feedback, bool):
                    # special handling for default escalation scenarios
                    feedback = str(feedback)
                return HumanResponseEvent(response=feedback)
        return None

    def _serialize_object(self, obj):
        """Recursively serializes an object and all its nested components."""
        # Handle Pydantic models
        if hasattr(obj, "model_dump"):
            return self._serialize_object(obj.model_dump(by_alias=True))
        elif hasattr(obj, "dict"):
            return self._serialize_object(obj.dict())
        elif hasattr(obj, "to_dict"):
            return self._serialize_object(obj.to_dict())
        # Handle dictionaries
        elif isinstance(obj, dict):
            return {k: self._serialize_object(v) for k, v in obj.items()}
        # Handle lists
        elif isinstance(obj, list):
            return [self._serialize_object(item) for item in obj]
        # Handle other iterable objects (convert to dict first)
        elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
            try:
                return self._serialize_object(dict(obj))
            except (TypeError, ValueError):
                return obj
        # Return primitive types as is
        else:
            return obj
