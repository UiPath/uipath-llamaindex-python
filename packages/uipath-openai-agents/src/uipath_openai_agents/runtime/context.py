"""Context type detection utilities for OpenAI Agents."""

import inspect
from typing import Any, get_args, get_origin

from agents import Agent
from pydantic import BaseModel


def get_agent_context_type(agent: Agent) -> type[BaseModel] | None:
    """Extract the context type from Agent[TContext] generic parameter."""
    context_type = None

    # Check __orig_class__ (set when instantiating with type parameter)
    orig_class = getattr(agent, "__orig_class__", None)
    if orig_class:
        args = get_args(orig_class)
        if args:
            context_type = args[0]

    # Check class-level __orig_bases__ for subclassed agents
    if context_type is None:
        for base in getattr(agent.__class__, "__orig_bases__", []):
            origin = get_origin(base)
            if origin and _is_agent_class(origin):
                args = get_args(base)
                if args:
                    context_type = args[0]
                    break

    if context_type and _is_pydantic_model(context_type):
        return context_type
    return None


def parse_input_to_context(
    input_dict: dict[str, Any] | None, context_type: type[BaseModel]
) -> BaseModel:
    """Parse input dict into a Pydantic context model (excludes 'messages' field)."""
    data = dict(input_dict) if input_dict else {}
    data.pop("messages", None)  # messages is separate, not part of context
    try:
        return context_type.model_validate(data)
    except Exception as e:
        raise ValueError(f"Failed to parse context: {e}")


def _is_agent_class(cls: Any) -> bool:
    try:
        return cls is Agent or (inspect.isclass(cls) and issubclass(cls, Agent))
    except TypeError:
        return False


def _is_pydantic_model(type_hint: Any) -> bool:
    try:
        return inspect.isclass(type_hint) and issubclass(type_hint, BaseModel)
    except TypeError:
        return False


__all__ = [
    "get_agent_context_type",
    "parse_input_to_context",
]
