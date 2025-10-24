from enum import Enum
from typing import Optional, Union

from uipath._cli._runtime._contracts import (
    UiPathBaseRuntimeError,
    UiPathErrorCategory,
    UiPathErrorCode,
)


class LLamaIndexErrorCode(Enum):
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
        code: Union[LLamaIndexErrorCode, UiPathErrorCode],
        title: str,
        detail: str,
        category: UiPathErrorCategory = UiPathErrorCategory.UNKNOWN,
        status: Optional[int] = None,
    ):
        super().__init__(
            code.value, title, detail, category, status, prefix="LlamaIndex"
        )
