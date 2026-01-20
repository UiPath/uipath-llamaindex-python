"""Demonstration of schema extraction from OpenAI Agents."""

import json

from agents import Agent
from pydantic import BaseModel, Field

from uipath_openai_agents.runtime.schema import get_entrypoints_schema


# Define output model
class SupportResponse(BaseModel):
    """Customer support response output."""

    response: str = Field(description="Agent's response to the customer")
    status: str = Field(
        description="Status of the query (resolved, pending, escalated)"
    )
    follow_up_needed: bool = Field(
        default=False, description="Whether follow-up is required"
    )
    resolution_time_seconds: float = Field(
        description="Time taken to resolve the query"
    )


# Create agent WITH output_type
support_agent_with_schema = Agent(
    name="support_agent",
    instructions="You are a helpful customer support agent",
    output_type=SupportResponse,
)

# Create agent WITHOUT output_type (for comparison)
support_agent_without_schema = Agent(
    name="support_agent",
    instructions="You are a helpful customer support agent",
)


def main():
    """Demonstrate schema extraction."""
    print("=" * 80)
    print("Schema Extraction for OpenAI Agents")
    print("=" * 80)

    # Extract schema from agent with output_type
    print("\n1. Schema WITH output_type (native OpenAI Agents pattern):")
    print("-" * 80)
    schema_with_output_type = get_entrypoints_schema(support_agent_with_schema)
    print(json.dumps(schema_with_output_type, indent=2))

    # Extract schema from agent without output_type
    print("\n\n2. Schema WITHOUT output_type (default fallback):")
    print("-" * 80)
    schema_without_output_type = get_entrypoints_schema(support_agent_without_schema)
    print(json.dumps(schema_without_output_type, indent=2))

    # Show the difference
    print("\n\n" + "=" * 80)
    print("Key Differences:")
    print("=" * 80)
    print("\nWith output_type:")
    print(
        f"  - Input properties: {list(schema_with_output_type['input']['properties'].keys())}"
    )
    print(
        f"  - Required inputs: {schema_with_output_type['input'].get('required', [])}"
    )
    print(
        f"  - Output properties: {list(schema_with_output_type['output']['properties'].keys())}"
    )
    print(
        f"  - Required outputs: {schema_with_output_type['output'].get('required', [])}"
    )

    print("\nWithout output_type (default):")
    print(
        f"  - Input properties: {list(schema_without_output_type['input']['properties'].keys())}"
    )
    print(
        f"  - Required inputs: {schema_without_output_type['input'].get('required', [])}"
    )
    print(
        f"  - Output properties: {list(schema_without_output_type['output']['properties'].keys())}"
    )
    print(
        f"  - Required outputs: {schema_without_output_type['output'].get('required', [])}"
    )

    print("\n" + "=" * 80)
    print("✓ Schema extraction uses agent.output_type for structured outputs!")
    print("=" * 80)


if __name__ == "__main__":
    main()
