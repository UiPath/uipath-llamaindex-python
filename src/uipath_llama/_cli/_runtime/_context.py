from typing import Optional

from uipath._cli._runtime._contracts import UiPathRuntimeContext

from .._utils._config import LlamaConfig


class UiPathLlamaRuntimeContext(UiPathRuntimeContext):
    """Context information passed throughout the runtime execution."""

    config: Optional[LlamaConfig] = None
