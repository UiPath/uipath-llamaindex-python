"""Factory for creating OpenAI Agents runtimes from openai_agents.json configuration."""

import asyncio
import os
from typing import Any

from agents import Agent
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from uipath.core.tracing import UiPathSpanUtils
from uipath.runtime import (
    UiPathRuntimeContext,
    UiPathRuntimeProtocol,
)
from uipath.runtime.errors import UiPathErrorCategory

from uipath_openai_agents.runtime._telemetry import get_current_span_wrapper
from uipath_openai_agents.runtime.agent import OpenAiAgentLoader
from uipath_openai_agents.runtime.config import OpenAiAgentsConfig
from uipath_openai_agents.runtime.errors import (
    UiPathOpenAIAgentsErrorCode,
    UiPathOpenAIAgentsRuntimeError,
)
from uipath_openai_agents.runtime.runtime import UiPathOpenAIAgentRuntime
from uipath_openai_agents.runtime.storage import SqliteAgentStorage


class UiPathOpenAIAgentRuntimeFactory:
    """Factory for creating OpenAI Agent runtimes from openai_agents.json configuration."""

    def __init__(
        self,
        context: UiPathRuntimeContext,
    ):
        """
        Initialize the factory.

        Args:
            context: UiPathRuntimeContext to use for runtime creation
        """
        self.context = context
        self._config: OpenAiAgentsConfig | None = None

        self._agent_cache: dict[str, Agent] = {}
        self._agent_loaders: dict[str, OpenAiAgentLoader] = {}
        self._agent_lock = asyncio.Lock()

        self._storage: SqliteAgentStorage | None = None
        self._storage_lock = asyncio.Lock()

        self._setup_instrumentation()

    def _setup_instrumentation(self) -> None:
        """Setup tracing and instrumentation."""
        OpenAIAgentsInstrumentor().instrument()
        UiPathSpanUtils.register_current_span_provider(get_current_span_wrapper)

    async def _get_or_create_storage(self) -> SqliteAgentStorage | None:
        """Get or create the shared storage instance.

        Returns:
            Shared storage instance, or None if storage is disabled
        """
        async with self._storage_lock:
            if self._storage is None:
                storage_path = self._get_storage_path()
                if storage_path:
                    self._storage = SqliteAgentStorage(storage_path)
                    await self._storage.setup()
            return self._storage

    def _get_storage_path(self) -> str | None:
        """Get the storage path for agent state.

        Returns:
            Path to SQLite database for storage, or None if storage is disabled
        """
        if self.context.runtime_dir and self.context.state_file:
            path = os.path.join(self.context.runtime_dir, self.context.state_file)

            if not self.context.resume and self.context.job_id is None:
                # If not resuming and no job id, delete the previous state file
                if os.path.exists(path):
                    os.remove(path)

            os.makedirs(self.context.runtime_dir, exist_ok=True)
            return path

        return None

    def _get_storage_path_legacy(self, runtime_id: str) -> str | None:
        """
        Get the storage path for agent session state.

        Args:
            runtime_id: Unique identifier for the runtime instance

        Returns:
            Path to SQLite database for session storage, or None if storage is disabled
        """
        if self.context.runtime_dir and self.context.state_file:
            # Use state file name pattern but with runtime_id
            base_name = os.path.splitext(self.context.state_file)[0]
            file_name = f"{base_name}_{runtime_id}.db"
            path = os.path.join(self.context.runtime_dir, file_name)

            if not self.context.resume and self.context.job_id is None:
                # If not resuming and no job id, delete the previous state file
                if os.path.exists(path):
                    os.remove(path)

            os.makedirs(self.context.runtime_dir, exist_ok=True)
            return path

        # Default storage path
        default_dir = os.path.join("__uipath", "sessions")
        os.makedirs(default_dir, exist_ok=True)
        return os.path.join(default_dir, f"{runtime_id}.db")

    def _load_config(self) -> OpenAiAgentsConfig:
        """Load openai_agents.json configuration."""
        if self._config is None:
            self._config = OpenAiAgentsConfig()
        return self._config

    async def _load_agent(self, entrypoint: str) -> Agent:
        """
        Load an agent for the given entrypoint.

        Args:
            entrypoint: Name of the agent to load

        Returns:
            The loaded Agent

        Raises:
            UiPathOpenAIAgentRuntimeError: If agent cannot be loaded
        """
        config = self._load_config()
        if not config.exists:
            raise UiPathOpenAIAgentsRuntimeError(
                UiPathOpenAIAgentsErrorCode.CONFIG_MISSING,
                "Invalid configuration",
                "Failed to load openai_agents.json configuration",
                UiPathErrorCategory.DEPLOYMENT,
            )

        if entrypoint not in config.agents:
            available = ", ".join(config.entrypoint)
            raise UiPathOpenAIAgentsRuntimeError(
                UiPathOpenAIAgentsErrorCode.AGENT_NOT_FOUND,
                "Agent not found",
                f"Agent '{entrypoint}' not found. Available: {available}",
                UiPathErrorCategory.DEPLOYMENT,
            )

        path = config.agents[entrypoint]
        agent_loader = OpenAiAgentLoader.from_path_string(entrypoint, path)

        self._agent_loaders[entrypoint] = agent_loader

        try:
            return await agent_loader.load()
        except UiPathOpenAIAgentsRuntimeError:
            # Re-raise our own errors as-is
            raise
        except ImportError as e:
            raise UiPathOpenAIAgentsRuntimeError(
                UiPathOpenAIAgentsErrorCode.AGENT_IMPORT_ERROR,
                "Agent import failed",
                f"Failed to import agent '{entrypoint}': {str(e)}",
                UiPathErrorCategory.USER,
            ) from e
        except TypeError as e:
            raise UiPathOpenAIAgentsRuntimeError(
                UiPathOpenAIAgentsErrorCode.AGENT_TYPE_ERROR,
                "Invalid agent type",
                f"Agent '{entrypoint}' is not a valid OpenAI Agent: {str(e)}",
                UiPathErrorCategory.USER,
            ) from e
        except ValueError as e:
            raise UiPathOpenAIAgentsRuntimeError(
                UiPathOpenAIAgentsErrorCode.AGENT_VALUE_ERROR,
                "Invalid agent value",
                f"Invalid value in agent '{entrypoint}': {str(e)}",
                UiPathErrorCategory.USER,
            ) from e
        except Exception as e:
            raise UiPathOpenAIAgentsRuntimeError(
                UiPathOpenAIAgentsErrorCode.AGENT_LOAD_ERROR,
                "Failed to load agent",
                f"Unexpected error loading agent '{entrypoint}': {str(e)}",
                UiPathErrorCategory.USER,
            ) from e

    async def _resolve_agent(self, entrypoint: str) -> Agent:
        """
        Resolve an agent from configuration.
        Results are cached for reuse across multiple runtime instances.

        Args:
            entrypoint: Name of the agent to resolve

        Returns:
            The loaded Agent ready for execution

        Raises:
            UiPathOpenAIAgentRuntimeError: If resolution fails
        """
        async with self._agent_lock:
            if entrypoint in self._agent_cache:
                return self._agent_cache[entrypoint]

            loaded_agent = await self._load_agent(entrypoint)
            self._agent_cache[entrypoint] = loaded_agent

            return loaded_agent

    def discover_entrypoints(self) -> list[str]:
        """
        Discover all agent entrypoints.

        Returns:
            List of agent names that can be used as entrypoints
        """
        config = self._load_config()
        if not config.exists:
            return []
        return config.entrypoint

    async def discover_runtimes(self) -> list[UiPathRuntimeProtocol]:
        """
        Discover runtime instances for all entrypoints.

        Returns:
            List of OpenAI Agent runtime instances, one per entrypoint
        """
        entrypoints = self.discover_entrypoints()

        runtimes: list[UiPathRuntimeProtocol] = []
        for entrypoint in entrypoints:
            agent = await self._resolve_agent(entrypoint)

            runtime = await self._create_runtime_instance(
                agent=agent,
                runtime_id=entrypoint,
                entrypoint=entrypoint,
            )
            runtimes.append(runtime)

        return runtimes

    async def _create_runtime_instance(
        self,
        agent: Agent,
        runtime_id: str,
        entrypoint: str,
    ) -> UiPathRuntimeProtocol:
        """
        Create a runtime instance from an agent.

        Args:
            agent: The OpenAI Agent
            runtime_id: Unique identifier for the runtime instance
            entrypoint: Agent entrypoint name

        Returns:
            Configured runtime instance
        """
        # Get shared storage instance
        storage = await self._get_or_create_storage()
        storage_path = storage.storage_path if storage else None

        # Get the loaded object from the agent loader for schema inference
        loaded_object = None
        if entrypoint in self._agent_loaders:
            loaded_object = self._agent_loaders[entrypoint].get_loaded_object()

        return UiPathOpenAIAgentRuntime(
            agent=agent,
            runtime_id=runtime_id,
            entrypoint=entrypoint,
            storage_path=storage_path,
            debug_mode=self.context.command == "debug",
            loaded_object=loaded_object,
            storage=storage,
        )

    async def new_runtime(
        self, entrypoint: str, runtime_id: str, **kwargs: Any
    ) -> UiPathRuntimeProtocol:
        """
        Create a new OpenAI Agent runtime instance.

        Args:
            entrypoint: Agent name from openai_agents.json
            runtime_id: Unique identifier for the runtime instance
            **kwargs: Additional keyword arguments (unused)

        Returns:
            Configured runtime instance with agent
        """
        agent = await self._resolve_agent(entrypoint)

        return await self._create_runtime_instance(
            agent=agent,
            runtime_id=runtime_id,
            entrypoint=entrypoint,
        )

    async def dispose(self) -> None:
        """Cleanup factory resources."""
        for loader in self._agent_loaders.values():
            await loader.cleanup()

        self._agent_loaders.clear()
        self._agent_cache.clear()

        # Dispose shared storage
        if self._storage:
            await self._storage.dispose()
            self._storage = None
