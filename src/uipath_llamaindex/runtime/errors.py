from enum import Enum

from uipath.runtime.errors import (
    UiPathBaseRuntimeError,
    UiPathErrorCategory,
    UiPathErrorCode,
)


class UiPathLlamaIndexErrorCode(Enum):
    AGENT_EXECUTION_FAILURE = "AGENT_EXECUTION_FAILURE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    SERIALIZE_OUTPUT_ERROR = "SERIALIZE_OUTPUT_ERROR"

    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"

    WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"
    WORKFLOW_TYPE_ERROR = "WORKFLOW_TYPE_ERROR"
    WORKFLOW_VALUE_ERROR = "WORKFLOW_VALUE_ERROR"
    WORKFLOW_LOAD_ERROR = "WORKFLOW_LOAD_ERROR"
    WORKFLOW_IMPORT_ERROR = "WORKFLOW_IMPORT_ERROR"


class UiPathLlamaIndexRuntimeError(UiPathBaseRuntimeError):
    """Custom exception for LlamaIndex runtime errors with structured error information."""

    def __init__(
        self,
        code: UiPathLlamaIndexErrorCode | UiPathErrorCode,
        title: str,
        detail: str,
        category: UiPathErrorCategory = UiPathErrorCategory.UNKNOWN,
        status: int | None = None,
    ):
        super().__init__(
            code.value, title, detail, category, status, prefix="LlamaIndex"
        )
