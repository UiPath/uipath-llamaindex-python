"""Demonstration of parameter inference from type annotations."""

import json

from agents import Agent
from pydantic import BaseModel, Field

from uipath_openai_agents.runtime.schema import get_entrypoints_schema


# Define input/output models
class CustomerQuery(BaseModel):
    """Customer support query input."""

    customer_id: str = Field(description="Unique customer identifier")
    message: str = Field(description="Customer's question or issue")
    priority: int = Field(default=1, description="Priority level (1-5)", ge=1, le=5)
    category: str | None = Field(
        default=None, description="Optional category classification"
    )


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


# Create agent
support_agent = Agent(
    name="support_agent",
    instructions="You are a helpful customer support agent",
)


async def handle_customer_query(query: CustomerQuery) -> SupportResponse:
    """
    Handle a customer support query.

    Args:
        query: The customer's query with context

    Returns:
        A structured response from the support agent
    """
    # Implementation would go here
    return SupportResponse(
        response="Thank you for contacting us!",
        status="resolved",
        follow_up_needed=False,
        resolution_time_seconds=1.5,
    )


def main():
    """Demonstrate schema inference."""
    print("=" * 80)
    print("Parameter Inference for OpenAI Agents")
    print("=" * 80)

    # Extract schema with type inference
    print("\n1. Schema WITH type annotations (from wrapper function):")
    print("-" * 80)
    schema_with_types = get_entrypoints_schema(support_agent, handle_customer_query)
    print(json.dumps(schema_with_types, indent=2))

    # Extract schema without type inference
    print("\n\n2. Schema WITHOUT type annotations (default fallback):")
    print("-" * 80)
    schema_without_types = get_entrypoints_schema(support_agent, None)
    print(json.dumps(schema_without_types, indent=2))

    # Show the difference
    print("\n\n" + "=" * 80)
    print("Key Differences:")
    print("=" * 80)
    print("\nWith type annotations:")
    print(
        f"  - Input properties: {list(schema_with_types['input']['properties'].keys())}"
    )
    print(f"  - Required inputs: {schema_with_types['input'].get('required', [])}")
    print(
        f"  - Output properties: {list(schema_with_types['output']['properties'].keys())}"
    )
    print(f"  - Required outputs: {schema_with_types['output'].get('required', [])}")

    print("\nWithout type annotations (default):")
    print(
        f"  - Input properties: {list(schema_without_types['input']['properties'].keys())}"
    )
    print(f"  - Required inputs: {schema_without_types['input'].get('required', [])}")
    print(
        f"  - Output properties: {list(schema_without_types['output']['properties'].keys())}"
    )
    print(f"  - Required outputs: {schema_without_types['output'].get('required', [])}")

    print("\n" + "=" * 80)
    print("✓ Parameter inference extracts rich type information automatically!")
    print("=" * 80)


if __name__ == "__main__":
    main()
