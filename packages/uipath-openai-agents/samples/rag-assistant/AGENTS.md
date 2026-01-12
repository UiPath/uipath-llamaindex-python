# OpenAI Agents SDK with UiPath Integration

This document provides patterns for building coded agents using the **OpenAI Agents SDK** with UiPath.

---

## Quick Reference

### Agent Pattern (OpenAI Agents SDK)

```python
from agents import Agent, Runner

# Define your agent
my_agent = Agent(
    name="my_agent",
    instructions="You are a helpful assistant...",
    model="gpt-4o",  # Optional: defaults to gpt-4o
    tools=[],  # Optional: add tools for capabilities
)

# Register in openai_agents.json:
# {
#   "agents": {
#     "agent": "main.py:my_agent"
#   }
# }
```

### Input Format

OpenAI Agents use **simple message input**:

```json
{
  "message": "Your question here"
}
```

Or for conversation history:

```json
{
  "messages": [
    {"role": "user", "content": "First message"},
    {"role": "assistant", "content": "Response"},
    {"role": "user", "content": "Follow-up"}
  ]
}
```

**No Pydantic Input/Output models required** - the runtime handles conversion automatically!

---

## Key Concepts

### 1. Agent Definition

```python
from agents import Agent

assistant = Agent(
    name="assistant_agent",  # Used in logs and diagrams
    instructions="Your system prompt here",
    model="gpt-4o",  # Optional
    tools=[tool1, tool2],  # Optional
)
```

### 2. Running Agents

**Via UiPath CLI** (recommended):
```bash
uipath run agent --file input.json
```

**Programmatically**:
```python
from agents import Runner

result = await Runner.run(
    starting_agent=assistant,
    input="User message"  # or list of message dicts
)
```

### 3. Tools (for RAG, APIs, etc.)

```python
from agents import tool

@tool
async def search_docs(query: str) -> str:
    """Search documentation for relevant info."""
    # Implementation here
    return results

# Add to agent:
agent = Agent(
    name="rag_agent",
    tools=[search_docs],
    instructions="Use search_docs to find information before answering."
)
```

### 4. UiPath Integration

The runtime **automatically injects UiPathChatOpenAI** client when credentials are available:

```bash
# Set these environment variables:
export UIPATH_URL="https://your-tenant.uipath.com"
export UIPATH_ORGANIZATION_ID="your-org-id"
export UIPATH_TENANT_ID="your-tenant-id"
export UIPATH_ACCESS_TOKEN="your-token"
```

All agents will use **UiPath LLM Gateway** instead of direct OpenAI!

---

## Project Structure

```
my-agent/
├── main.py              # Agent definition
├── openai_agents.json   # Agent registration
├── pyproject.toml       # Dependencies
├── input.json           # Test input
├── .env                 # Credentials (gitignored)
└── uipath.json          # Runtime config (auto-generated)
```

---

## Common Patterns

### Basic Q&A Agent

```python
from agents import Agent

qa_agent = Agent(
    name="qa_agent",
    instructions="Answer questions concisely and accurately."
)
```

### Agent with Tools (RAG)

```python
from agents import Agent, tool

@tool
async def retrieve_context(query: str) -> str:
    """Retrieve relevant context from knowledge base."""
    # Use UiPath Context Grounding or custom retriever
    return context

rag_agent = Agent(
    name="rag_agent",
    instructions="Use retrieve_context before answering questions.",
    tools=[retrieve_context]
)
```

### Multi-Agent (Handoffs)

```python
from agents import Agent

specialist = Agent(
    name="specialist",
    instructions="You are a domain expert..."
)

coordinator = Agent(
    name="coordinator",
    instructions="Route requests to the specialist when needed.",
    handoffs=[specialist]
)
```

---

## Testing

```bash
# Initialize project
uipath init

# Run agent
uipath run agent --file input.json

# With inline input
uipath run agent '{"message": "Hello!"}'

# Debug mode
uipath run agent --debug --file input.json
```

---

## Differences from LangGraph/LlamaIndex

| Aspect | OpenAI Agents SDK | LangGraph/LlamaIndex |
|--------|-------------------|----------------------|
| **Input** | `{"message": "..."}` | Pydantic Input model required |
| **Output** | Free-form response | Pydantic Output model required |
| **Agent Type** | Agentic (LLM decides) | Workflow-based (fixed graph) |
| **Tools** | `@tool` decorator | Custom tool classes |
| **Registration** | `openai_agents.json` | `uipath.json` functions |

---

## Resources

- **OpenAI Agents SDK**: https://github.com/openai/openai-agents-python
- **UiPath Python SDK**: https://uipath.github.io/uipath-python/
- **Samples**: Check `samples/` directory for examples

---

## Getting Help

If you need assistance:
- Check sample projects in `samples/`
- Review OpenAI Agents SDK documentation
- Open issues at https://github.com/anthropics/claude-code/issues
