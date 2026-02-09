"""Context type detection utilities for OpenAI Agents."""

import inspect
from typing import Any, get_args, get_origin

from agents import Agent
from pydantic import BaseModel


def get_agent_context_type(agent: Agent) -> type[BaseModel] | None:
    """Extract the context type from Agent[TContext] generic parameter."""
    # Agent[MyCtx](...) sets __orig_class__ on the instance
    orig_class = getattr(agent, "__orig_class__", None)
    if orig_class:
        args = get_args(orig_class)
        if args and inspect.isclass(args[0]) and issubclass(args[0], BaseModel):
            return args[0]

    # class MyAgent(Agent[MyCtx]) sets __orig_bases__ on the class
    for base in getattr(agent.__class__, "__orig_bases__", []):
        if get_origin(base) is Agent:
            args = get_args(base)
            if args and inspect.isclass(args[0]) and issubclass(args[0], BaseModel):
                return args[0]

    return None


def parse_input_to_context(
    input_dict: dict[str, Any] | None, context_type: type[BaseModel]
) -> BaseModel:
    """Parse input dict into a Pydantic context model (excludes 'messages' field)."""
    data = dict(input_dict) if input_dict else {}
    data.pop("messages", None)
    try:
        return context_type.model_validate(data)
    except Exception as e:
        raise ValueError(f"Failed to parse context: {e}") from e


__all__ = [
    "get_agent_context_type",
    "parse_input_to_context",
]
