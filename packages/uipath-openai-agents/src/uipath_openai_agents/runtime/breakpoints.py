"""Breakpoint support for OpenAI Agents runtime.

Note: OpenAI Agents SDK has limited breakpoint support compared to LlamaIndex
workflows due to the different execution model. Breakpoints are currently
implemented at the agent execution boundaries (before/after agent runs).

Future enhancements could include:
- Tool call breakpoints (before/after each tool execution)
- Handoff breakpoints (when transferring between agents)
- Custom breakpoint injection points
"""

from __future__ import annotations

from typing import Any

from agents import Agent


class BreakpointEvent:
    """Event emitted when a breakpoint is hit."""

    def __init__(self, breakpoint_node: str, **kwargs: Any):
        self.breakpoint_node = breakpoint_node
        self.data = kwargs


class BreakpointResumeEvent:
    """Event sent to resume execution from a breakpoint."""

    pass


def supports_breakpoints(agent: Agent) -> bool:
    """
    Check if the agent supports breakpoints.

    Currently, breakpoint support is limited in OpenAI Agents.
    This function is a placeholder for future enhancements.

    Args:
        agent: The OpenAI Agent instance

    Returns:
        False (breakpoints not yet fully supported)
    """
    return False


__all__ = [
    "BreakpointEvent",
    "BreakpointResumeEvent",
    "supports_breakpoints",
]
