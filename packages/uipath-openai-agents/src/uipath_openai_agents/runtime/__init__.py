"""
UiPath OpenAI Agents Runtime.

NOTE: This module uses lazy imports for most exports to avoid loading heavy
dependencies (openai SDK) at import time. However, the runtime factory
registration must happen eagerly for CLI discovery.
"""

from uipath.runtime import (
    UiPathRuntimeContext,
    UiPathRuntimeFactoryProtocol,
    UiPathRuntimeFactoryRegistry,
)


def register_runtime_factory() -> None:
    """Register the OpenAI Agents factory. Called automatically via entry point."""

    def create_factory(
        context: UiPathRuntimeContext | None = None,
    ) -> UiPathRuntimeFactoryProtocol:
        # Import lazily when factory is actually created
        from uipath_openai_agents.runtime.factory import (
            UiPathOpenAIAgentRuntimeFactory,
        )

        return UiPathOpenAIAgentRuntimeFactory(
            context=context if context else UiPathRuntimeContext(),
        )

    UiPathRuntimeFactoryRegistry.register(
        "openai-agents", create_factory, "openai_agents.json"
    )


# Register factory eagerly (required for CLI discovery)
register_runtime_factory()


def __getattr__(name):
    if name == "get_entrypoints_schema":
        from .schema import get_entrypoints_schema

        return get_entrypoints_schema
    if name == "get_agent_schema":
        from .schema import get_agent_schema

        return get_agent_schema
    if name == "UiPathOpenAIAgentRuntimeFactory":
        from .factory import UiPathOpenAIAgentRuntimeFactory

        return UiPathOpenAIAgentRuntimeFactory
    if name == "UiPathOpenAIAgentRuntime":
        from .runtime import UiPathOpenAIAgentRuntime

        return UiPathOpenAIAgentRuntime
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "register_runtime_factory",
    "get_entrypoints_schema",
    "get_agent_schema",
    "UiPathOpenAIAgentRuntimeFactory",
    "UiPathOpenAIAgentRuntime",
]
