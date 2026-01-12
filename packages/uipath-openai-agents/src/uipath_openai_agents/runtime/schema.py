"""Schema extraction utilities for OpenAI Agents."""

from typing import Any

from agents import Agent
from pydantic import TypeAdapter
from uipath.runtime.schema import (
    UiPathRuntimeEdge,
    UiPathRuntimeGraph,
    UiPathRuntimeNode,
)


def get_entrypoints_schema(agent: Agent) -> dict[str, Any]:
    """
    Extract input/output schema from an OpenAI Agent.

    Args:
        agent: An OpenAI Agent instance

    Returns:
        Dictionary with input and output schemas
    """
    schema = {
        "input": {"type": "object", "properties": {}, "required": []},
        "output": {"type": "object", "properties": {}, "required": []},
    }

    # For OpenAI Agents, the standard input is a message or list of messages
    # This is the typical input format for conversational agents
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

    # Try to extract output schema from agent's output_type if available
    try:
        output_type = getattr(agent, "output_type", None)
        if output_type is not None:
            # Use Pydantic's TypeAdapter to generate schema for the output type
            adapter = TypeAdapter(output_type)
            output_schema = adapter.json_schema()

            # Resolve references and handle nullable types
            unpacked_output = _resolve_refs(output_schema)
            schema["output"]["properties"] = _process_nullable_types(
                unpacked_output.get("properties", {})
            )
            schema["output"]["required"] = unpacked_output.get("required", [])
        else:
            # Default output schema for agents without explicit output_type
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
    except (AttributeError, Exception):
        # Fallback to default output schema
        schema["output"] = {
            "type": "object",
            "properties": {
                "result": {
                    "title": "Result",
                    "description": "The agent's response",
                    "type": "object",
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
