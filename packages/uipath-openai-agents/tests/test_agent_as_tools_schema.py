"""Tests for agent-as-tools sample schema extraction."""

import sys
from pathlib import Path

# Add samples directory to path
samples_dir = Path(__file__).parent.parent / "samples" / "agent-as-tools"
sys.path.insert(0, str(samples_dir))

from main import (  # type: ignore  # noqa: E402
    TranslationInput,
    TranslationOutput,
    main,
    orchestrator_agent,
)

from uipath_openai_agents.runtime.schema import get_entrypoints_schema  # noqa: E402


def test_agent_as_tools_input_schema():
    """Test that input schema uses default messages format (OpenAI Agents pattern)."""
    schema = get_entrypoints_schema(orchestrator_agent, main)

    # Verify input schema structure - should use default messages
    assert "input" in schema
    assert "properties" in schema["input"]

    # OpenAI Agents use messages as input (not custom types)
    input_props = schema["input"]["properties"]
    assert "message" in input_props

    # Verify message field accepts string or array
    assert "anyOf" in input_props["message"]
    types = [t.get("type") for t in input_props["message"]["anyOf"]]
    assert "string" in types
    assert "array" in types

    # Check required fields
    assert "required" in schema["input"]
    assert "message" in schema["input"]["required"]


def test_agent_as_tools_output_schema():
    """Test that output schema is extracted from agent's output_type."""
    schema = get_entrypoints_schema(orchestrator_agent, main)

    # Verify output schema structure
    assert "output" in schema
    assert "properties" in schema["output"]

    # Check required output fields from agent's output_type
    output_props = schema["output"]["properties"]
    assert "original_text" in output_props
    assert "translations" in output_props
    assert "languages_used" in output_props

    # Verify field types
    assert output_props["original_text"]["type"] == "string"
    assert output_props["translations"]["type"] == "object"
    assert output_props["languages_used"]["type"] == "array"

    # Verify descriptions (from Field definitions)
    assert "description" in output_props["original_text"]
    assert "description" in output_props["translations"]
    assert "description" in output_props["languages_used"]

    # Check required fields
    assert "required" in schema["output"]
    assert "original_text" in schema["output"]["required"]
    assert "translations" in schema["output"]["required"]
    assert "languages_used" in schema["output"]["required"]


def test_agent_as_tools_schema_metadata():
    """Test that schema includes model metadata from agent's output_type."""
    schema = get_entrypoints_schema(orchestrator_agent, main)

    # Input uses default messages format (no custom title/description)
    assert "input" in schema
    assert "properties" in schema["input"]
    assert "message" in schema["input"]["properties"]

    # Check output metadata from agent's output_type
    assert "title" in schema["output"]
    assert schema["output"]["title"] == "TranslationOutput"
    assert "description" in schema["output"]
    assert "translation orchestrator" in schema["output"]["description"].lower()


def test_pydantic_models_are_valid():
    """Test that the Pydantic models themselves are valid."""
    # Test input model creation
    input_data = TranslationInput(text="Hello", target_languages=["Spanish", "French"])
    assert input_data.text == "Hello"
    assert input_data.target_languages == ["Spanish", "French"]

    # Test output model creation
    output_data = TranslationOutput(
        original_text="Hello",
        translations={"Spanish": "Hola", "French": "Bonjour"},
        languages_used=["Spanish", "French"],
    )
    assert output_data.original_text == "Hello"
    assert output_data.translations["Spanish"] == "Hola"
    assert len(output_data.languages_used) == 2
