from typing import Optional

from llama_index.core.workflow import Context, Workflow
from uipath._cli._runtime._contracts import UiPathResumeTrigger, UiPathRuntimeContext

from .._utils._config import LlamaIndexConfig


class UiPathLlamaIndexRuntimeContext(UiPathRuntimeContext):
    """Context information passed throughout the runtime execution."""

    config: Optional[LlamaIndexConfig] = None
    workflow: Optional[Workflow] = None
    workflow_context: Optional[Context] = None  # type: ignore[type-arg]
    resumed_trigger: Optional[UiPathResumeTrigger] = None
