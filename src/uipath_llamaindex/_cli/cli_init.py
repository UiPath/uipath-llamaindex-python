import asyncio
import json
import os
import uuid
from typing import Any, Callable, Dict, overload

from llama_index.core.workflow import (
    HumanResponseEvent,
    InputRequiredEvent,
    StopEvent,
    Workflow,
)
from llama_index.core.workflow.drawing import StepConfig  # type: ignore
from llama_index.core.workflow.utils import (  # type: ignore
    get_steps_from_class,
    get_steps_from_instance,
)
from uipath._cli._utils._console import ConsoleLogger
from uipath._cli._utils._parse_ast import generate_bindings_json  # type: ignore
from uipath._cli.middlewares import MiddlewareResult

from ._utils._config import LlamaIndexConfig

console = ConsoleLogger()


def resolve_refs(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve references in a schema"""
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        if "definitions" in schema and ref in schema["definitions"]:
            return resolve_refs(schema["definitions"][ref])

    properties = schema.get("properties", {})
    for prop, prop_schema in properties.items():
        if "$ref" in prop_schema:
            properties[prop] = resolve_refs(prop_schema)

    return schema


def process_nullable_types(properties: Dict[str, Any]) -> Dict[str, Any]:
    """Process properties to handle nullable types correctly"""
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


def generate_schema_from_workflow(workflow: Workflow) -> Dict[str, Any]:
    """Extract input/output schema from a LlamaIndex workflow"""
    schema = {
        "input": {"type": "object", "properties": {}, "required": []},
        "output": {"type": "object", "properties": {}, "required": []},
    }

    # Find the actual StartEvent and StopEvent classes used in this workflow
    start_event_class = workflow._start_event_class
    stop_event_class = workflow._stop_event_class

    # Generate input schema from StartEvent using Pydantic's schema method
    try:
        input_schema = start_event_class.model_json_schema()
        # Resolve references and handle nullable types
        input_schema = resolve_refs(input_schema)
        schema["input"]["properties"] = process_nullable_types(
            input_schema.get("properties", {})
        )
        schema["input"]["required"] = input_schema.get("required", [])
    except (AttributeError, Exception):
        pass

    # For output schema, check if it's the base StopEvent or a custom subclass
    if stop_event_class is StopEvent:
        # base StopEvent
        schema["output"] = {
            "type": "object",
            "properties": {
                "result": {
                    "title": "Result",
                    "type": "object",
                }
            },
            "required": ["result"],
        }
    else:
        # For custom StopEvent subclasses, extract their Pydantic schema
        try:
            output_schema = stop_event_class.model_json_schema()
            # Resolve references and handle nullable types
            output_schema = resolve_refs(output_schema)
            schema["output"]["properties"] = process_nullable_types(
                output_schema.get("properties", {})
            )
            schema["output"]["required"] = output_schema.get("required", [])
        except (AttributeError, Exception):
            pass

    return schema


def draw_all_possible_flows_mermaid(
    workflow: Workflow,
    filename: str = "workflow_all_flows.mermaid",
) -> str:
    """Draws all possible flows of the workflow as a Mermaid diagram."""
    # Initialize Mermaid flowchart string
    mermaid_diagram = ["flowchart TD"]

    # Add nodes from all steps
    steps = get_steps_from_class(workflow)
    if not steps:
        # If no steps are defined in the class, try to get them from the instance
        steps = get_steps_from_instance(workflow)

    # Track all nodes and edges to avoid duplicates
    nodes = set()
    edges = set()

    # Track event types to avoid duplicates
    event_types = {}
    current_stop_event = (
        None  # Only one kind of `StopEvent` is allowed in a `Workflow`.
    )
    step_config: StepConfig | None = None

    for _, step_func in steps.items():
        step_config = getattr(step_func, "__step_config", None)
        if step_config is None:
            continue

        for return_type in step_config.return_types:
            if issubclass(return_type, StopEvent):
                current_stop_event = return_type
                break

        if current_stop_event:
            break

    # First pass: collect all event types (both return types and accepted events)
    for _, step_func in steps.items():
        step_config = getattr(step_func, "__step_config", None)
        if step_config is None:
            continue

        # Collect accepted event types
        for event_type in step_config.accepted_events:
            if event_type == StopEvent and event_type != current_stop_event:
                continue

            event_name = event_type.__name__
            event_types[event_name] = event_type

        # Collect return types
        for return_type in step_config.return_types:
            if return_type is type(None):
                continue

            return_name = return_type.__name__
            event_types[return_name] = return_type

    # Generate step nodes
    for step_name, step_func in steps.items():
        step_config = getattr(step_func, "__step_config", None)
        if step_config is None:
            continue

        # Add step node (use step_name with cleaned ID)
        step_id = f"step_{clean_id(step_name)}"
        if step_id not in nodes:
            nodes.add(step_id)
            mermaid_diagram.append(f'    {step_id}["{step_name}"]:::stepStyle')

    # Generate event nodes (only once per event type)
    for event_name, event_type in event_types.items():
        event_id = f"event_{clean_id(event_name)}"
        if event_id not in nodes:
            nodes.add(event_id)
            style = get_event_style(event_type)
            mermaid_diagram.append(f"    {event_id}([<p>{event_name}</p>]):::{style}")

        if issubclass(event_type, InputRequiredEvent):
            # Add node for conceptual external step
            if "external_step" not in nodes:
                nodes.add("external_step")
                mermaid_diagram.append(
                    '    external_step["external_step"]:::externalStyle'
                )

    # Generate edges
    for step_name, step_func in steps.items():
        step_config = getattr(step_func, "__step_config", None)
        if step_config is None:
            continue

        step_id = f"step_{clean_id(step_name)}"

        # Add edges for return types
        for return_type in step_config.return_types:
            if return_type is not type(None):
                return_name = return_type.__name__
                return_id = f"event_{clean_id(return_name)}"
                edge = f"{step_id} --> {return_id}"
                if edge not in edges:
                    edges.add(edge)
                    mermaid_diagram.append(f"    {edge}")

            if issubclass(return_type, InputRequiredEvent):
                return_name = return_type.__name__
                return_id = f"event_{clean_id(return_name)}"
                edge = f"{return_id} --> external_step"
                if edge not in edges:
                    edges.add(edge)
                    mermaid_diagram.append(f"    {edge}")

        # Add edges for accepted events
        for event_type in step_config.accepted_events:
            event_name = event_type.__name__
            event_id = f"event_{clean_id(event_name)}"

            if step_name == "_done" and issubclass(event_type, StopEvent):
                if current_stop_event:
                    stop_event_name = current_stop_event.__name__
                    stop_event_id = f"event_{clean_id(stop_event_name)}"
                    edge = f"{stop_event_id} --> {step_id}"
                    if edge not in edges:
                        edges.add(edge)
                        mermaid_diagram.append(f"    {edge}")
            else:
                edge = f"{event_id} --> {step_id}"
                if edge not in edges:
                    edges.add(edge)
                    mermaid_diagram.append(f"    {edge}")

            if issubclass(event_type, HumanResponseEvent):
                edge = f"external_step --> {event_id}"
                if edge not in edges:
                    edges.add(edge)
                    mermaid_diagram.append(f"    {edge}")

    # Add style definitions
    mermaid_diagram.append("    classDef stepStyle fill:#f2f0ff,line-height:1.2")
    mermaid_diagram.append("    classDef externalStyle fill:#f2f0ff,line-height:1.2")
    mermaid_diagram.append("    classDef defaultEventStyle fill-opacity:0")
    mermaid_diagram.append("    classDef stopEventStyle fill:#bfb6fc")
    mermaid_diagram.append(
        "    classDef inputRequiredStyle fill:#f2f0ff,line-height:1.2"
    )

    # Join all lines
    mermaid_string = "\n".join(mermaid_diagram)

    # Write to file if filename is provided
    if filename:
        with open(filename, "w") as f:
            f.write(mermaid_string)

    return mermaid_string


def clean_id(name: str) -> str:
    """Convert a name to a valid Mermaid ID."""
    # Replace invalid characters with underscores
    return name.replace(" ", "_").replace("-", "_").replace(".", "_")


def get_event_style(event_type) -> str:
    """Return the appropriate Mermaid style class for an event type."""
    if issubclass(event_type, StopEvent):
        return "stopEventStyle"
    elif issubclass(event_type, InputRequiredEvent):
        return "inputRequiredStyle"
    else:
        return "defaultEventStyle"


async def llamaindex_init_middleware_async(
    entrypoint: str,
    options: dict[str, Any] | None = None,
    write_config: Callable[[Any], str] | None = None,
) -> MiddlewareResult:
    """Middleware to check for llama_index.json and create uipath.json with schemas"""
    options = options or {}

    config = LlamaIndexConfig()
    if not config.exists:
        return MiddlewareResult(
            should_continue=True
        )  # Continue with normal flow if no llama_index.json

    try:
        config.load_config()
        entrypoints = []
        all_bindings = {"version": "2.0", "resources": []}

        for workflow in config.workflows:
            if entrypoint and workflow.name != entrypoint:
                continue

            try:
                loaded_workflow = await workflow.load_workflow()
                schema = generate_schema_from_workflow(loaded_workflow)
                try:
                    should_infer_bindings = options.get("infer_bindings", True)
                    # Make sure the file path exists
                    if os.path.exists(workflow.file_path) and should_infer_bindings:
                        file_bindings = generate_bindings_json(workflow.file_path)
                        # Merge bindings
                        if "resources" in file_bindings:
                            all_bindings["resources"] = file_bindings["resources"]
                except Exception as e:
                    console.warning(
                        f"Warning: Could not generate bindings for {workflow.file_path}: {str(e)}"
                    )
                new_entrypoint: dict[str, Any] = {
                    "filePath": workflow.name,
                    "uniqueId": str(uuid.uuid4()),
                    "type": "agent",
                    "input": schema["input"],
                    "output": schema["output"],
                }
                entrypoints.append(new_entrypoint)

                draw_all_possible_flows_mermaid(
                    loaded_workflow, filename=f"{workflow.name}.mermaid"
                )

            except Exception as e:
                console.error(f"Error during workflow load: {e}")
                return MiddlewareResult(
                    should_continue=False,
                    should_include_stacktrace=True,
                )
            finally:
                await workflow.cleanup()

        if entrypoint and not entrypoints:
            console.error(f"Error: No workflow found with name '{entrypoint}'")
            return MiddlewareResult(
                should_continue=False,
            )

        uipath_config = {"entryPoints": entrypoints, "bindings": all_bindings}

        if write_config:
            config_path = write_config(uipath_config)
        else:
            # Save the uipath.json file
            config_path = "uipath.json"
            with open(config_path, "w") as f:
                json.dump(uipath_config, f, indent=4)

        console.success(f" Created '{config_path}' file.")
        return MiddlewareResult(should_continue=False)

    except Exception as e:
        console.error(f"Error processing LlamaIndex configuration: {str(e)}")
        return MiddlewareResult(
            should_continue=False,
            should_include_stacktrace=True,
        )


@overload
def llamaindex_init_middleware(entrypoint: str) -> MiddlewareResult: ...


@overload
def llamaindex_init_middleware(
    entrypoint: str,
    options: dict[str, Any],
    write_config: Callable[[Any], str],
) -> MiddlewareResult: ...


def llamaindex_init_middleware(
    entrypoint: str,
    options: dict[str, Any] | None = None,
    write_config: Callable[[Any], str] | None = None,
) -> MiddlewareResult:
    """Middleware to check for llama_index.json and create uipath.json with schemas"""
    return asyncio.run(
        llamaindex_init_middleware_async(entrypoint, options, write_config)
    )
