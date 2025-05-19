import logging
from typing import Optional

from uipath import UiPath
from uipath._cli._runtime._contracts import (
    UiPathBaseRuntime,
    UiPathErrorCategory,
    UiPathRuntimeResult,
)
from uipath.tracing import wait_for_tracers

from ._context import UiPathLlamaRuntimeContext
from ._exception import UiPathLlamaRuntimeError

logger = logging.getLogger(__name__)


class UiPathLlamaRuntime(UiPathBaseRuntime):
    """
    A runtime class for hosting UiPath Llama agents.
    """

    def __init__(self, context: UiPathLlamaRuntimeContext):
        super().__init__(context)
        self.context: UiPathLlamaRuntimeContext = context
        self._uipath = UiPath()

    async def execute(self) -> Optional[UiPathRuntimeResult]:
        """
        Start the Llama agent runtime.

        Returns:
            Dictionary with execution results

        Raises:
            UiPathLlamaRuntimeError: If execution fails
        """
        await self.validate()

        try:
            a = 2

        except Exception as e:
            if isinstance(e, UiPathLlamaRuntimeError):
                raise
            detail = f"Error: {str(e)}"
            raise UiPathLlamaRuntimeError(
                "EXECUTION_ERROR",
                "Llama Runtime execution failed",
                detail,
                UiPathErrorCategory.USER,
            ) from e
        finally:
            wait_for_tracers()

    async def validate(self) -> None:
        """Validate runtime inputs and load Llama agent configuration."""
        pass

    async def cleanup(self) -> None:
        """Clean up all resources."""
        pass
