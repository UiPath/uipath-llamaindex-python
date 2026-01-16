"""Tests for parameter inference from type annotations."""

from agents import Agent
from pydantic import BaseModel

from uipath_openai_agents.runtime.schema import get_entrypoints_schema


class OutputModel(BaseModel):
    """Test output model."""

    response: str
    agent_used: str
    confidence: float


# Test agent with output_type (native OpenAI Agents pattern)
agent_with_output_type = Agent(
    name="test_agent_with_output",
    instructions="Test agent with output_type",
    output_type=OutputModel,
)

# Test agent without output_type
test_agent = Agent(
    name="test_agent",
    instructions="Test agent for schema inference",
)


def test_schema_inference_from_agent_output_type():
    """Test that output schema is correctly inferred from agent's output_type (PRIMARY)."""
    schema = get_entrypoints_schema(agent_with_output_type, None)

    # Check input schema - should be default messages format
    assert "input" in schema
    assert "properties" in schema["input"]
    assert "message" in schema["input"]["properties"]
    assert "required" in schema["input"]
    assert "message" in schema["input"]["required"]

    # Check output schema - extracted from agent's output_type
    assert "output" in schema
    assert "properties" in schema["output"]
    assert "response" in schema["output"]["properties"]
    assert "agent_used" in schema["output"]["properties"]
    assert "confidence" in schema["output"]["properties"]

    # Check all output fields are required (no defaults)
    assert "required" in schema["output"]
    assert "response" in schema["output"]["required"]
    assert "agent_used" in schema["output"]["required"]
    assert "confidence" in schema["output"]["required"]

    # Verify title is included
    assert schema["output"].get("title") == "OutputModel"


def test_schema_fallback_without_types():
    """Test that schemas fall back to defaults when no types are provided."""
    schema = get_entrypoints_schema(test_agent, None)

    # Should use default message-based input schema
    assert "input" in schema
    assert "message" in schema["input"]["properties"]

    # Should fall back to default result-based output
    assert "output" in schema
    assert "result" in schema["output"]["properties"]


def test_schema_with_plain_agent():
    """Test schema extraction with a plain agent (no wrapper function)."""
    schema = get_entrypoints_schema(test_agent, test_agent)

    # Should use default message input
    assert "input" in schema
    assert "message" in schema["input"]["properties"]

    # Should use default result output
    assert "output" in schema
    assert "result" in schema["output"]["properties"]


class WrapperOutputModel(BaseModel):
    """Output model for wrapper function test."""

    status: str
    data: dict[str, str]


async def typed_wrapper_function(message: str) -> WrapperOutputModel:
    """Wrapper function with type annotations (UiPath pattern - SECONDARY)."""
    return WrapperOutputModel(status="success", data={})


def test_schema_with_wrapper_function():
    """Test that wrapper function output schema is used as fallback (SECONDARY)."""
    # Agent without output_type should fallback to wrapper function
    schema = get_entrypoints_schema(test_agent, typed_wrapper_function)

    # Input should still be default messages (not extracted from wrapper)
    assert "input" in schema
    assert "message" in schema["input"]["properties"]
    assert "required" in schema["input"]
    assert "message" in schema["input"]["required"]

    # Output should come from wrapper function (secondary pattern)
    assert "output" in schema
    assert "properties" in schema["output"]
    assert "status" in schema["output"]["properties"]
    assert "data" in schema["output"]["properties"]
