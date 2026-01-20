"""Error handling for OpenAI Agents runtime."""

from enum import Enum

from uipath.runtime.errors import (
    UiPathBaseRuntimeError,
    UiPathErrorCategory,
    UiPathErrorCode,
)


class UiPathOpenAIAgentsErrorCode(Enum):
    """Error codes specific to OpenAI Agents runtime."""

    AGENT_EXECUTION_FAILURE = "AGENT_EXECUTION_FAILURE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    SERIALIZE_OUTPUT_ERROR = "SERIALIZE_OUTPUT_ERROR"

    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"

    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_TYPE_ERROR = "AGENT_TYPE_ERROR"
    AGENT_VALUE_ERROR = "AGENT_VALUE_ERROR"
    AGENT_LOAD_ERROR = "AGENT_LOAD_ERROR"
    AGENT_IMPORT_ERROR = "AGENT_IMPORT_ERROR"


class UiPathOpenAIAgentsRuntimeError(UiPathBaseRuntimeError):
    """Custom exception for OpenAI Agents runtime errors with structured error information."""

    def __init__(
        self,
        code: UiPathOpenAIAgentsErrorCode | UiPathErrorCode,
        title: str,
        detail: str,
        category: UiPathErrorCategory = UiPathErrorCategory.UNKNOWN,
        status: int | None = None,
    ):
        super().__init__(
            code.value, title, detail, category, status, prefix="OpenAI-Agents"
        )


__all__ = [
    "UiPathOpenAIAgentsErrorCode",
    "UiPathOpenAIAgentsRuntimeError",
]
