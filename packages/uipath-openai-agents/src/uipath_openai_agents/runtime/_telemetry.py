"""OpenTelemetry tracing integration for OpenAI Agents."""

from typing import Any

try:
    from agents import Agent, AgentHooks
    from opentelemetry import trace
    from opentelemetry.trace import Span, Status, StatusCode

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False


if TELEMETRY_AVAILABLE:

    class TelemetryHooks(AgentHooks):
        """AgentHooks implementation that creates OpenTelemetry spans for agent lifecycle events."""

        def __init__(self, tracer: trace.Tracer):
            """Initialize telemetry hooks.

            Args:
                tracer: OpenTelemetry tracer for creating spans
            """
            self.tracer = tracer
            self._spans: dict[str, Span] = {}

        async def on_start(
            self,
            _context: Any,
            agent: Any,
        ) -> None:
            """Called when agent execution starts."""
            agent_name = getattr(agent, "name", "unknown")
            model = getattr(agent, "model", None)
            model_name = str(model) if model else "unknown"

            span = self.tracer.start_span(
                f"agent.{agent_name}",
                attributes={
                    "agent.name": agent_name,
                    "agent.model": model_name,
                },
            )
            self._spans["agent"] = span

        async def on_end(
            self,
            _context: Any,
            _agent: Any,
            _output: Any,
        ) -> None:
            """Called when agent execution completes."""
            span = self._spans.pop("agent", None)
            if span:
                span.set_status(Status(StatusCode.OK))
                span.end()

        async def on_llm_start(
            self,
            _context: Any,
            agent: Any,
            _system_prompt: Any,
            input_items: Any,
        ) -> None:
            """Called when LLM call starts."""
            model = getattr(agent, "model", None)
            model_name = str(model) if model else "unknown"

            span = self.tracer.start_span(
                f"llm.{model_name}",
                attributes={
                    "llm.model": model_name,
                    "llm.input_items_count": len(input_items) if input_items else 0,
                },
            )
            self._spans["llm"] = span

        async def on_llm_end(
            self,
            _context: Any,
            _agent: Any,
            _response: Any,
        ) -> None:
            """Called when LLM call completes."""
            span = self._spans.pop("llm", None)
            if span:
                span.set_status(Status(StatusCode.OK))
                span.end()

        async def on_tool_start(
            self,
            _context: Any,
            _agent: Any,
            tool: Any,
        ) -> None:
            """Called when tool execution starts."""
            tool_name = getattr(tool, "name", None) or getattr(tool, "__name__", "unknown")

            span = self.tracer.start_span(
                f"tool.{tool_name}",
                attributes={
                    "tool.name": tool_name,
                },
            )
            self._spans[f"tool_{tool_name}"] = span

        async def on_tool_end(
            self,
            _context: Any,
            _agent: Any,
            tool: Any,
            _result: Any,
        ) -> None:
            """Called when tool execution completes."""
            tool_name = getattr(tool, "name", None) or getattr(tool, "__name__", "unknown")
            span = self._spans.pop(f"tool_{tool_name}", None)
            if span:
                span.set_status(Status(StatusCode.OK))
                span.end()

        async def on_handoff(
            self,
            _context: Any,
            target_agent: Any,
            source_agent: Any,
        ) -> None:
            """Called when agent hands off to another agent."""
            source_name = getattr(source_agent, "name", "unknown")
            target_name = getattr(target_agent, "name", "unknown")

            span = self.tracer.start_span(
                f"handoff.{source_name}_to_{target_name}",
                attributes={
                    "handoff.source": source_name,
                    "handoff.target": target_name,
                },
            )
            span.end()

    def create_telemetry_hooks(enabled: bool = True) -> Any | None:
        """Create telemetry hooks for OpenAI Agents.

        Args:
            enabled: Whether telemetry should be enabled

        Returns:
            TelemetryHooks instance if telemetry is available and enabled, None otherwise
        """
        if not enabled:
            return None

        tracer = trace.get_tracer(__name__)
        return TelemetryHooks(tracer)

else:

    def create_telemetry_hooks(_enabled: bool = True) -> None:
        """Create telemetry hooks for OpenAI Agents.

        Args:
            _enabled: Whether telemetry should be enabled (unused when telemetry not available)

        Returns:
            None since telemetry dependencies are not available
        """
        return None


__all__ = ["create_telemetry_hooks"]
