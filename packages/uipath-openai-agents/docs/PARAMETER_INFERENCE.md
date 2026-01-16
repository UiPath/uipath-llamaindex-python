# Parameter Inference for OpenAI Agents

## Overview

The `uipath-openai-agents` package now automatically infers input/output schemas from Pydantic type annotations. This enables rich, type-safe interfaces for OpenAI agents integrated with UiPath workflows.

## How It Works

When you define a wrapper function with Pydantic `BaseModel` type annotations, the schema extraction system automatically:

1. Inspects the function's type hints
2. Extracts Pydantic model schemas
3. Generates JSON schemas for input and output
4. Includes field descriptions, constraints, and default values

If no type annotations are found, the system falls back to a generic message/result schema.

## Usage Example

### With Type Annotations (Recommended)

```python
from agents import Agent
from pydantic import BaseModel, Field

class CustomerQuery(BaseModel):
    """Customer support query input."""
    customer_id: str = Field(description="Unique customer identifier")
    message: str = Field(description="Customer's question or issue")
    priority: int = Field(default=1, description="Priority level (1-5)", ge=1, le=5)

class SupportResponse(BaseModel):
    """Customer support response output."""
    response: str = Field(description="Agent's response to the customer")
    status: str = Field(description="Status of the query")

support_agent = Agent(
    name="support_agent",
    instructions="You are a helpful customer support agent",
)

async def handle_query(query: CustomerQuery) -> SupportResponse:
    """Handle customer support queries."""
    # Implementation here
    pass
```

The extracted schema will include:
- **Input fields**: `customer_id`, `message`, `priority`
- **Required inputs**: `customer_id`, `message` (priority has a default)
- **Output fields**: `response`, `status`
- **All metadata**: descriptions, constraints (min/max), defaults

### Without Type Annotations (Fallback)

```python
support_agent = Agent(
    name="support_agent",
    instructions="You are a helpful customer support agent",
)
```

The extracted schema will use defaults:
- **Input**: Generic `message` field
- **Output**: Generic `result` field

## Configuration in openai_agents.json

To use parameter inference, reference your typed wrapper function in the configuration:

```json
{
  "agents": {
    "support": "main.py:handle_query"
  }
}
```

The loader will:
1. Load the `handle_query` function
2. Extract the resolved `Agent` from it
3. Store the original function for schema inference
4. Generate schemas from the function's type annotations

## Schema Features

### Extracted from Pydantic Models

- ✅ Field types (string, integer, float, boolean, array, object)
- ✅ Field descriptions (from `Field(description="...")`)
- ✅ Default values
- ✅ Required vs. optional fields
- ✅ Constraints (minimum, maximum, pattern, etc.)
- ✅ Nullable types
- ✅ Nested models
- ✅ Model titles and descriptions

### Example Schema Output

```json
{
  "input": {
    "type": "object",
    "title": "CustomerQuery",
    "description": "Customer support query input.",
    "properties": {
      "customer_id": {
        "type": "string",
        "title": "Customer Id",
        "description": "Unique customer identifier"
      },
      "message": {
        "type": "string",
        "title": "Message",
        "description": "Customer's question or issue"
      },
      "priority": {
        "type": "integer",
        "title": "Priority",
        "description": "Priority level (1-5)",
        "default": 1,
        "minimum": 1,
        "maximum": 5
      }
    },
    "required": ["customer_id", "message"]
  },
  "output": {
    "type": "object",
    "title": "SupportResponse",
    "description": "Customer support response output.",
    "properties": {
      "response": {
        "type": "string",
        "title": "Response",
        "description": "Agent's response to the customer"
      },
      "status": {
        "type": "string",
        "title": "Status",
        "description": "Status of the query"
      }
    },
    "required": ["response", "status"]
  }
}
```

## Benefits

1. **Type Safety**: Catch type errors at design time
2. **Self-Documenting**: Schemas include descriptions and constraints
3. **IDE Support**: Get autocomplete and inline documentation
4. **Validation**: Pydantic validates input/output automatically
5. **UiPath Integration**: Rich schemas enable better Studio experience
6. **Backward Compatible**: Falls back to defaults if no types are provided

## Implementation Details

### Files Modified

- `src/uipath_openai_agents/runtime/agent.py`: Store original loaded object
- `src/uipath_openai_agents/runtime/schema.py`: Add parameter inference logic
- `src/uipath_openai_agents/runtime/factory.py`: Pass loaded object to runtime
- `src/uipath_openai_agents/runtime/runtime.py`: Use loaded object for schema

### Key Functions

- `_is_pydantic_model()`: Check if a type hint is a Pydantic model
- `_extract_schema_from_callable()`: Extract schemas from callable's type hints
- `get_entrypoints_schema()`: Main schema extraction (now supports loaded objects)

## Testing

Run the demonstration:
```bash
uv run python tests/demo_schema_inference.py
```

Run the tests:
```bash
uv run pytest tests/test_schema_inference.py -v
```

## See Also

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OpenAI Agents Python SDK](https://github.com/openai/openai-agents-python)
- [Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
