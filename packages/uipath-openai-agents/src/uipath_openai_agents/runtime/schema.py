"""Schema extraction utilities for OpenAI Agents."""

import inspect
from typing import Any, get_args, get_origin

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


def get_entrypoints_schema(agent: Agent) -> dict[str, Any]:
    """
    Extract input/output schema from an OpenAI Agent.

    Uses the agent's native output_type attribute for schema extraction.

    Args:
        agent: An OpenAI Agent instance

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
            "messages": {
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "array",
                        "items": {"type": "object"},
                    },
                ],
                "title": "Messages",
                "description": "User messages to send to the agent",
            }
        },
        "required": ["messages"],
    }

    # Extract output schema - Agent's output_type (native OpenAI Agents pattern)
    output_type = getattr(agent, "output_type", None)
    output_extracted = False

    # Unwrap AgentOutputSchema if present (OpenAI Agents SDK wrapper)
    # AgentOutputSchema wraps the actual Pydantic model in an 'output_type' attribute
    if (
        output_type is not None
        and hasattr(output_type, "output_type")
        and not isinstance(output_type, type)
    ):
        # This is an AgentOutputSchema wrapper instance, extract the actual model
        output_type = output_type.output_type

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

    OpenAI Agents are represented as simple nodes. Regular tools are aggregated
    into a single tools node per agent with metadata. Agent-tools and handoff
    agents are represented as separate agent nodes.

    Args:
        agent: An OpenAI Agent instance

    Returns:
        UiPathRuntimeGraph with nodes and edges representing the agent structure
    """
    nodes: list[UiPathRuntimeNode] = []
    edges: list[UiPathRuntimeEdge] = []
    visited: set[str] = set()  # Track visited agents to avoid circular references

    def _add_agent_and_tools(current_agent: Agent) -> None:
        """Recursively add agent, its tools, and nested agents to the graph."""
        agent_name = getattr(current_agent, "name", "agent")

        # Prevent circular references using agent name
        if agent_name in visited:
            return
        visited.add(agent_name)

        # Add agent node (first visit always adds the node)
        nodes.append(
            UiPathRuntimeNode(
                id=agent_name,
                name=agent_name,
                type="node",
                subgraph=None,
                metadata=None,
            )
        )

        # Process tools - separate agent-tools from regular tools
        tools = getattr(current_agent, "tools", None) or []
        agent_tools: list[Agent] = []
        regular_tools: list[Any] = []

        for tool in tools:
            if isinstance(tool, Agent):
                agent_tools.append(tool)
            else:
                regular_tools.append(tool)

        # Process agent-tools (agents used as tools)
        for tool_agent in agent_tools:
            tool_agent_name = getattr(tool_agent, "name", _get_tool_name(tool_agent))
            if tool_agent_name and tool_agent_name not in visited:
                # Recursively process agent-tool
                _add_agent_and_tools(tool_agent)

                # Add edges for agent-tool
                edges.append(
                    UiPathRuntimeEdge(
                        source=agent_name,
                        target=tool_agent_name,
                        label="tool_call",
                    )
                )
                edges.append(
                    UiPathRuntimeEdge(
                        source=tool_agent_name,
                        target=agent_name,
                        label="tool_result",
                    )
                )

        # Process regular tools - aggregate into single tools node
        if regular_tools:
            tool_names = [_get_tool_name(tool) for tool in regular_tools]
            tool_names = [name for name in tool_names if name]  # Filter out None values

            if tool_names:
                # Create a single tools node for this agent
                tools_node_id = f"{agent_name}_tools"
                nodes.append(
                    UiPathRuntimeNode(
                        id=tools_node_id,
                        name="tools",
                        type="tool",
                        subgraph=None,
                        metadata={
                            "tool_names": tool_names,
                            "tool_count": len(tool_names),
                        },
                    )
                )

                # Add bidirectional edges for tools node
                edges.append(
                    UiPathRuntimeEdge(
                        source=agent_name,
                        target=tools_node_id,
                        label=None,
                    )
                )
                edges.append(
                    UiPathRuntimeEdge(
                        source=tools_node_id,
                        target=agent_name,
                        label=None,
                    )
                )

        # Process handoff agents
        handoffs = getattr(current_agent, "handoffs", None) or []
        for handoff_agent in handoffs:
            handoff_name = getattr(handoff_agent, "name", None)
            if handoff_name and handoff_name not in visited:
                # Recursively process handoff agent
                _add_agent_and_tools(handoff_agent)

                # Add handoff edges without labels
                edges.append(
                    UiPathRuntimeEdge(
                        source=agent_name,
                        target=handoff_name,
                        label=None,
                    )
                )
                edges.append(
                    UiPathRuntimeEdge(
                        source=handoff_name,
                        target=agent_name,
                        label=None,
                    )
                )

    # Add __start__ node
    nodes.append(
        UiPathRuntimeNode(
            id="__start__",
            name="__start__",
            type="__start__",
            subgraph=None,
            metadata=None,
        )
    )

    # Recursively build graph starting from main agent
    _add_agent_and_tools(agent)

    # Get the main agent name
    agent_name = getattr(agent, "name", "agent")

    # Add __end__ node
    nodes.append(
        UiPathRuntimeNode(
            id="__end__",
            name="__end__",
            type="__end__",
            subgraph=None,
            metadata=None,
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

    # Connect main agent to end
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
