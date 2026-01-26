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
    """Test that output schema is correctly inferred from agent's output_type."""
    schema = get_entrypoints_schema(agent_with_output_type)

    # Check input schema - should be default messages format
    assert "input" in schema
    assert "properties" in schema["input"]
    assert "messages" in schema["input"]["properties"]
    assert "required" in schema["input"]
    assert "messages" in schema["input"]["required"]

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
    schema = get_entrypoints_schema(test_agent)

    # Should use default messages-based input schema
    assert "input" in schema
    assert "messages" in schema["input"]["properties"]

    # Should fall back to default result-based output
    assert "output" in schema
    assert "result" in schema["output"]["properties"]


def test_schema_with_plain_agent():
    """Test schema extraction with a plain agent."""
    schema = get_entrypoints_schema(test_agent)

    # Should use default messages input
    assert "input" in schema
    assert "messages" in schema["input"]["properties"]

    # Should use default result output
    assert "output" in schema
    assert "result" in schema["output"]["properties"]
