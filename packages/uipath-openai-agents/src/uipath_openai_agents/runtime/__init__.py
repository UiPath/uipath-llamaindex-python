"""UiPath OpenAI Agents Runtime."""

from uipath.runtime import (
    UiPathRuntimeContext,
    UiPathRuntimeFactoryProtocol,
    UiPathRuntimeFactoryRegistry,
)

from uipath_openai_agents.runtime.factory import UiPathOpenAIAgentRuntimeFactory
from uipath_openai_agents.runtime.runtime import UiPathOpenAIAgentRuntime
from uipath_openai_agents.runtime.schema import (
    get_agent_schema,
    get_entrypoints_schema,
)


def register_runtime_factory() -> None:
    """Register the OpenAI Agents factory. Called automatically via entry point."""

    def create_factory(
        context: UiPathRuntimeContext | None = None,
    ) -> UiPathRuntimeFactoryProtocol:
        return UiPathOpenAIAgentRuntimeFactory(
            context=context if context else UiPathRuntimeContext(),
        )

    UiPathRuntimeFactoryRegistry.register(
        "openai-agents", create_factory, "openai_agents.json"
    )


register_runtime_factory()

__all__ = [
    "register_runtime_factory",
    "get_entrypoints_schema",
    "get_agent_schema",
    "UiPathOpenAIAgentRuntimeFactory",
    "UiPathOpenAIAgentRuntime",
]
