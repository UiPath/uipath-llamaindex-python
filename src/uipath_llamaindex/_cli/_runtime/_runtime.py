import json
import logging
from typing import Optional

from uipath import UiPath
from uipath._cli._runtime._contracts import (
    UiPathBaseRuntime,
    UiPathErrorCategory,
    UiPathRuntimeResult,
)
from uipath.tracing import wait_for_tracers

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
        self._uipath = UiPath()

    async def execute(self) -> Optional[UiPathRuntimeResult]:
        """
        Start the LlamaIndex agent runtime.

        Returns:
            Dictionary with execution results

        Raises:
            UiPathLlamaIndexRuntimeError: If execution fails
        """
        await self.validate()

        try:
            start_event_class = self.context.workflow._start_event_class

            ev = start_event_class(**self.context.input_json)

            handler = self.context.workflow.run(start_event=ev)

            async for event in handler.stream_events():
                print(event)

            output = await handler

            self.context.result = UiPathRuntimeResult(
                output=self._serialize_object(output)
            )

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
            wait_for_tracers()

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
