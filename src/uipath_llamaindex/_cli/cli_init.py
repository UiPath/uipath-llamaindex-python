import asyncio
import inspect
import json
import os
import uuid
from typing import Any, Dict, Optional, Type, get_type_hints

from llama_index.core.workflow import Event, StartEvent, StopEvent, Workflow
from llama_index.core.workflow.decorators import StepConfig
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


def find_event_types(workflow: Workflow, event_base_class: Type[Event]) -> Type[Event]:
    """Find the StartEvent or StopEvent class in a workflow"""
    event_classes = set()

    # Get all steps from the workflow
    steps = {}

    # Get steps defined as methods
    for name, method in inspect.getmembers(workflow, inspect.ismethod):
        if hasattr(method, "__step_config"):
            steps[name] = method

    # Get steps defined as free functions
    class_steps = getattr(workflow.__class__, "_step_functions", {})
    steps.update(class_steps)

    # Find all event types that are subclasses of event_base_class
    for step_func in steps.values():
        step_config: Optional[StepConfig] = getattr(step_func, "__step_config")

        if event_base_class is StartEvent:
            # Look in accepted_events for StartEvent
            for event_type in step_config.accepted_events:
                if issubclass(event_type, event_base_class):
                    event_classes.add(event_type)
        else:
            # Look in return_types for StopEvent
            for event_type in step_config.return_types:
                if issubclass(event_type, event_base_class):
                    event_classes.add(event_type)

    if len(event_classes) == 1:
        return event_classes.pop()
    elif len(event_classes) > 1:
        # Return the most specific one (the one with the most fields)
        return max(event_classes, key=lambda cls: len(get_type_hints(cls)))
    return event_base_class  # Default fallback


def generate_schema_from_workflow(workflow: Workflow) -> Dict[str, Any]:
    """Extract input/output schema from a LlamaIndex workflow"""
    schema = {
        "input": {"type": "object", "properties": {}, "required": []},
        "output": {"type": "object", "properties": {}, "required": []},
    }

    # Find the actual StartEvent and StopEvent classes used in this workflow
    start_event_class = find_event_types(workflow, StartEvent)
    stop_event_class = find_event_types(workflow, StopEvent)

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
        # For base StopEvent, just use Any type for the result
        schema["output"] = {"type": "object", "properties": {}, "required": []}
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


async def llamaindex_init_middleware_async(entrypoint: str) -> MiddlewareResult:
    """Middleware to check for llama_index.json and create uipath.json with schemas"""
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
                    # Make sure the file path exists
                    if os.path.exists(workflow.file_path):
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

        # Save the uipath.json file
        config_path = "uipath.json"
        with open(config_path, "w") as f:
            json.dump(uipath_config, f, indent=2)

        console.success(f" Created '{config_path}' file.")
        return MiddlewareResult(should_continue=False)

    except Exception as e:
        console.error(f"Error processing LlamaIndex configuration: {str(e)}")
        return MiddlewareResult(
            should_continue=False,
            should_include_stacktrace=True,
        )


def llamaindex_init_middleware(entrypoint: str) -> MiddlewareResult:
    """Middleware to check for llama_index.json and create uipath.json with schemas"""
    return asyncio.run(llamaindex_init_middleware_async(entrypoint))
