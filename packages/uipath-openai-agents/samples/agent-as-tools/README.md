# Agent-as-Tools Sample

This sample demonstrates the **agents-as-tools pattern** for OpenAI Agents, adapted for UiPath coded workflows with **automatic parameter inference**.

## Overview

In this pattern:
1. **Specialist agents** handle specific tasks (Spanish, French, Italian translation)
2. **Orchestrator agent** uses specialist agents as tools
3. **Type-safe interfaces** are defined using Pydantic models
4. **Schemas are automatically inferred** from type annotations

## Pattern: Agents as Tools

The agents-as-tools pattern allows agents to call other agents as if they were tools. This creates a hierarchy where:

- The **orchestrator agent** receives user input and decides which specialist agents to call
- Each **specialist agent** is exposed as a tool using `.as_tool()`
- The orchestrator can call multiple specialists in sequence or parallel

## Parameter Inference

This sample showcases **automatic parameter inference** - a key feature of the `uipath-openai-agents` package.

### Input Model

```python
class TranslationInput(BaseModel):
    """Input model for the translation orchestrator."""

    text: str = Field(description="The English text to translate")
    target_languages: list[str] = Field(
        description="List of target languages (e.g., ['Spanish', 'French', 'Italian'])"
    )
```

**Automatically generates:**
- Input schema with 2 properties: `text` and `target_languages`
- Field descriptions for UiPath Studio
- Type validation (string and list of strings)

### Output Model

```python
class TranslationOutput(BaseModel):
    """Output model for the translation orchestrator."""

    original_text: str = Field(description="The original English text")
    translations: dict[str, str] = Field(
        description="Dictionary mapping language names to translated text"
    )
    languages_used: list[str] = Field(
        description="List of languages that were translated to"
    )
```

**Automatically generates:**
- Output schema with 3 properties
- Dictionary type for translations
- Rich metadata for workflow designers

### Agent Configuration

```python
from agents import Agent, AgentOutputSchema

orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions="...",
    tools=[...],
    output_type=AgentOutputSchema(TranslationOutput, strict_json_schema=False),
)
```

**Note**: The `AgentOutputSchema` wrapper with `strict_json_schema=False` is required when using `dict[str, str]` types, as they're not compatible with OpenAI's strict JSON schema mode. For strict-compatible types (e.g., lists, primitives, specific Pydantic models), you can use `output_type=YourModel` directly.

## Usage with UiPath

### Configuration

Configure the agent in `openai_agents.json`:

```json
{
  "agents": {
    "translator": "samples/agent-as-tools/main.py:main"
  }
}
```

### What Happens

When loaded by UiPath:
1. The runtime loads the `main` function
2. Extracts the `orchestrator_agent` from it
3. Analyzes `TranslationInput` and `TranslationOutput` types
4. Generates rich schemas automatically
5. Exposes the agent in Studio with full type information

### In UiPath Studio

The agent appears with:
- **Input properties**: `text`, `target_languages`
- **Output properties**: `original_text`, `translations`, `languages_used`
- **Field descriptions**: Visible in property panels
- **Type validation**: Enforced at design and runtime

## Key Benefits

1. **Type Safety**: Pydantic validation prevents errors
2. **Self-Documenting**: Schemas include descriptions
3. **UiPath Native**: Seamless Studio integration
4. **Automatic Schemas**: No manual schema definition needed

## Learn More

- [OpenAI Agents Python SDK](https://github.com/openai/openai-agents-python)
