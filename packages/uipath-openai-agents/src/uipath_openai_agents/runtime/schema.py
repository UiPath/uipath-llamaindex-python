"""Schema extraction utilities for OpenAI Agents."""

import inspect
from typing import Any, get_args, get_origin, get_type_hints

from agents import Agent
from pydantic import BaseModel, TypeAdapter
from uipath.runtime.schema import (
    UiPathRuntimeEdge,
    UiPathRuntimeGraph,
    UiPathRuntimeNode,
)


def _is_pydantic_model(type_hint: Any) -> bool:
    """
    Check if a type hint is a Pydantic BaseModel.

    Args:
        type_hint: A type hint from type annotations

    Returns:
        True if the type is a Pydantic model, False otherwise
    """
    try:
        # Direct check
        if inspect.isclass(type_hint) and issubclass(type_hint, BaseModel):
            return True

        # Handle generic types (e.g., Optional[Model])
        origin = get_origin(type_hint)
        if origin is not None:
            args = get_args(type_hint)
            for arg in args:
                if inspect.isclass(arg) and issubclass(arg, BaseModel):
                    return True

    except TypeError:
        pass

    return False


def _extract_schema_from_callable(callable_obj: Any) -> dict[str, Any] | None:
    """
    Extract input/output schemas from a callable's type annotations.

    Args:
        callable_obj: A callable object (function, async function, etc.)

    Returns:
        Dictionary with input and output schemas if type hints are found,
        None otherwise
    """
    if not callable(callable_obj):
        return None

    try:
        # Get type hints from the callable
        type_hints = get_type_hints(callable_obj)

        if not type_hints:
            return None

        # Get function signature to identify parameters
        sig = inspect.signature(callable_obj)
        params = list(sig.parameters.values())

        # Find the first parameter (usually the input)
        input_type = None

        for param in params:
            if param.name in ("self", "cls"):
                continue
            if param.name in type_hints:
                input_type = type_hints[param.name]
                break

        # Get return type
        return_type = type_hints.get("return")

        schema: dict[str, Any] = {
            "input": {"type": "object", "properties": {}, "required": []},
            "output": {"type": "object", "properties": {}, "required": []},
        }

        # Extract input schema from Pydantic model
        if input_type and _is_pydantic_model(input_type):
            adapter = TypeAdapter(input_type)
            input_schema = adapter.json_schema()
            unpacked_input = _resolve_refs(input_schema)

            schema["input"]["properties"] = _process_nullable_types(
                unpacked_input.get("properties", {})
            )
            schema["input"]["required"] = unpacked_input.get("required", [])

            # Add title and description if available
            if "title" in unpacked_input:
                schema["input"]["title"] = unpacked_input["title"]
            if "description" in unpacked_input:
                schema["input"]["description"] = unpacked_input["description"]

        # Extract output schema from Pydantic model
        if return_type and _is_pydantic_model(return_type):
            adapter = TypeAdapter(return_type)
            output_schema = adapter.json_schema()
            unpacked_output = _resolve_refs(output_schema)

            schema["output"]["properties"] = _process_nullable_types(
                unpacked_output.get("properties", {})
            )
            schema["output"]["required"] = unpacked_output.get("required", [])

            # Add title and description if available
            if "title" in unpacked_output:
                schema["output"]["title"] = unpacked_output["title"]
            if "description" in unpacked_output:
                schema["output"]["description"] = unpacked_output["description"]

        # Only return schema if we found at least one Pydantic model
        if schema["input"]["properties"] or schema["output"]["properties"]:
            return schema

    except Exception:
        # If schema extraction fails, return None to fall back to default
        pass

    return None


def get_entrypoints_schema(
    agent: Agent, loaded_object: Any | None = None
) -> dict[str, Any]:
    """
    Extract input/output schema from an OpenAI Agent.

    Prioritizes the agent's native output_type attribute (OpenAI Agents pattern),
    with optional fallback to wrapper function type hints (UiPath pattern).

    Args:
        agent: An OpenAI Agent instance
        loaded_object: Optional original loaded object (function/callable) with type annotations

    Returns:
        Dictionary with input and output schemas
    """
    schema = {
        "input": {"type": "object", "properties": {}, "required": []},
        "output": {"type": "object", "properties": {}, "required": []},
    }

    # Extract input schema - check agent's context type or use default messages
    # For OpenAI Agents, input is typically messages (string or list of message objects)
    schema["input"] = {
        "type": "object",
        "properties": {
            "message": {
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                ],
                "title": "Message",
                "description": "User message(s) to send to the agent",
            }
        },
        "required": ["message"],
    }

    # Extract output schema - PRIORITY 1: Agent's output_type (native OpenAI Agents pattern)
    output_type = getattr(agent, "output_type", None)
    output_extracted = False

    # Unwrap AgentOutputSchema if present (OpenAI Agents SDK wrapper)
    # Check for AgentOutputSchema by looking for 'schema' attribute on non-type instances
    if (
        output_type is not None
        and hasattr(output_type, "schema")
        and not isinstance(output_type, type)
    ):
        # This is an AgentOutputSchema wrapper instance, extract the actual model
        output_type = output_type.schema

    if output_type is not None and _is_pydantic_model(output_type):
        try:
            adapter = TypeAdapter(output_type)
            output_schema = adapter.json_schema()

            # Resolve references and handle nullable types
            unpacked_output = _resolve_refs(output_schema)
            schema["output"]["properties"] = _process_nullable_types(
                unpacked_output.get("properties", {})
            )
            schema["output"]["required"] = unpacked_output.get("required", [])

            # Add title and description if available
            if "title" in unpacked_output:
                schema["output"]["title"] = unpacked_output["title"]
            if "description" in unpacked_output:
                schema["output"]["description"] = unpacked_output["description"]

            output_extracted = True
        except Exception:
            # Continue to fallback if extraction fails
            pass

    # Extract output schema - PRIORITY 2: Wrapper function type hints (UiPath pattern)
    # This allows UiPath-specific patterns where agents are wrapped in typed functions
    if not output_extracted and loaded_object is not None:
        wrapper_schema = _extract_schema_from_callable(loaded_object)
        if wrapper_schema is not None:
            # Use the wrapper's output schema, but keep the default input (messages)
            schema["output"] = wrapper_schema["output"]
            output_extracted = True

    # Fallback: Default output schema for agents without explicit output_type
    if not output_extracted:
        schema["output"] = {
            "type": "object",
            "properties": {
                "result": {
                    "title": "Result",
                    "description": "The agent's response",
                    "anyOf": [
                        {"type": "string"},
                        {"type": "object"},
                        {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                    ],
                }
            },
            "required": ["result"],
        }

    return schema


def get_agent_schema(agent: Agent) -> UiPathRuntimeGraph:
    """
    Extract graph structure from an OpenAI Agent.

    OpenAI Agents can delegate to other agents through handoffs,
    creating a hierarchical agent structure.

    Args:
        agent: An OpenAI Agent instance

    Returns:
        UiPathRuntimeGraph with nodes and edges representing the agent structure
    """
    nodes: list[UiPathRuntimeNode] = []
    edges: list[UiPathRuntimeEdge] = []

    # Start node
    nodes.append(
        UiPathRuntimeNode(
            id="__start__",
            name="__start__",
            type="__start__",
            subgraph=None,
        )
    )

    # Main agent node (always type "model" since it's an LLM)
    agent_name = getattr(agent, "name", "agent")
    nodes.append(
        UiPathRuntimeNode(
            id=agent_name,
            name=agent_name,
            type="model",
            subgraph=None,
        )
    )

    # Connect start to main agent
    edges.append(
        UiPathRuntimeEdge(
            source="__start__",
            target=agent_name,
            label="input",
        )
    )

    # Add tool nodes if tools are available
    tools = getattr(agent, "tools", None) or []
    if tools:
        for tool in tools:
            # Extract tool name - handle various tool types
            tool_name = _get_tool_name(tool)
            if tool_name:
                nodes.append(
                    UiPathRuntimeNode(
                        id=tool_name,
                        name=tool_name,
                        type="tool",
                        subgraph=None,
                    )
                )
                # Bidirectional edges: agent calls tool, tool returns to agent
                edges.append(
                    UiPathRuntimeEdge(
                        source=agent_name,
                        target=tool_name,
                        label="tool_call",
                    )
                )
                edges.append(
                    UiPathRuntimeEdge(
                        source=tool_name,
                        target=agent_name,
                        label="tool_result",
                    )
                )

    # Add handoff agents as nodes
    handoffs = getattr(agent, "handoffs", None) or []
    if handoffs:
        for handoff_agent in handoffs:
            handoff_name = getattr(handoff_agent, "name", None)
            if handoff_name:
                nodes.append(
                    UiPathRuntimeNode(
                        id=handoff_name,
                        name=handoff_name,
                        type="model",
                        subgraph=None,  # Handoff agents are peers, not subgraphs
                    )
                )
                # Handoff edges
                edges.append(
                    UiPathRuntimeEdge(
                        source=agent_name,
                        target=handoff_name,
                        label="handoff",
                    )
                )
                edges.append(
                    UiPathRuntimeEdge(
                        source=handoff_name,
                        target=agent_name,
                        label="handoff_complete",
                    )
                )

    # End node
    nodes.append(
        UiPathRuntimeNode(
            id="__end__",
            name="__end__",
            type="__end__",
            subgraph=None,
        )
    )

    # Connect agent to end
    edges.append(
        UiPathRuntimeEdge(
            source=agent_name,
            target="__end__",
            label="output",
        )
    )

    return UiPathRuntimeGraph(nodes=nodes, edges=edges)


def _get_tool_name(tool: Any) -> str | None:
    """
    Extract the name of a tool from various tool types.

    Args:
        tool: A tool object (could be a function, class, or tool instance)

    Returns:
        The tool name as a string, or None if it cannot be determined
    """
    # Try common attributes for tool names
    if hasattr(tool, "name"):
        return str(tool.name)
    if hasattr(tool, "__name__"):
        return str(tool.__name__)
    if hasattr(tool, "tool_name"):
        return str(tool.tool_name)

    # For class-based tools, try to get class name
    if hasattr(tool, "__class__"):
        class_name = tool.__class__.__name__
        # Remove common suffixes like "Tool" for cleaner names
        if class_name.endswith("Tool"):
            return class_name[:-4].lower()
        return class_name.lower()

    return None


def _resolve_refs(
    schema: dict[str, Any],
    root: dict[str, Any] | None = None,
    visited: set[str] | None = None,
) -> dict[str, Any]:
    """
    Recursively resolves $ref references in a JSON schema.

    Args:
        schema: The schema dictionary to resolve
        root: The root schema for reference resolution
        visited: Set of visited references to detect circular dependencies

    Returns:
        Resolved schema dictionary
    """
    if root is None:
        root = schema

    if visited is None:
        visited = set()

    if isinstance(schema, dict):
        if "$ref" in schema:
            ref_path = schema["$ref"]

            if ref_path in visited:
                # Circular dependency detected
                return {
                    "type": "object",
                    "description": f"Circular reference to {ref_path}",
                }

            visited.add(ref_path)

            # Resolve the reference - handle both #/definitions/ and #/$defs/ formats
            ref_parts = ref_path.lstrip("#/").split("/")
            ref_schema = root
            for part in ref_parts:
                ref_schema = ref_schema.get(part, {})

            result = _resolve_refs(ref_schema, root, visited)

            # Remove from visited after resolution
            visited.discard(ref_path)

            return result

        return {k: _resolve_refs(v, root, visited) for k, v in schema.items()}

    elif isinstance(schema, list):
        return [_resolve_refs(item, root, visited) for item in schema]

    return schema


def _process_nullable_types(properties: dict[str, Any]) -> dict[str, Any]:
    """
    Process properties to handle nullable types correctly.

    This matches the original implementation that adds "nullable": True
    instead of simplifying the schema structure.

    Args:
        properties: The properties dictionary from a schema

    Returns:
        Processed properties with nullable types marked
    """
    result = {}
    for name, prop in properties.items():
        if "anyOf" in prop:
            types = [item.get("type") for item in prop["anyOf"] if "type" in item]
            if "null" in types:
                non_null_types = [t for t in types if t != "null"]
                if len(non_null_types) == 1:
                    result[name] = {"type": non_null_types[0], "nullable": True}
                else:
                    result[name] = {"type": non_null_types, "nullable": True}
            else:
                result[name] = prop
        else:
            result[name] = prop
    return result


__all__ = [
    "get_entrypoints_schema",
    "get_agent_schema",
]
