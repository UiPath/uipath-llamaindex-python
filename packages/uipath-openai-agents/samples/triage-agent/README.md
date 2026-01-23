# Triage Agent Sample - Language Routing with Handoffs

This sample demonstrates the **handoffs/routing pattern** for OpenAI Agents, adapted for UiPath coded workflows. The triage agent receives user messages and hands off to the appropriate specialist agent based on the language of the request.

## Pattern: Agent Routing with Handoffs

In this pattern:
1. **Triage agent** receives the user message
2. **Language detection** happens automatically by the LLM
3. **Handoff** to the appropriate specialist agent (French, Spanish, or English)
4. **Specialist agent** responds in their designated language
5. **Response streaming** provides real-time output

## Agents

### Triage Agent
- **Role**: Routes messages to language specialists
- **Instructions**: "Handoff to the appropriate agent based on the language of the request"
- **Handoffs**: French, Spanish, English agents

### Language Specialists
- **French Agent**: Only speaks French
- **Spanish Agent**: Only speaks Spanish
- **English Agent**: Only speaks English

## Usage

### Run with UiPath CLI

```bash
# Spanish message
uipath run main '{"messages": "Hola, ¿cómo estás?"}'

# French message
uipath run main '{"messages": "Bonjour, comment allez-vous?"}'

# English message
uipath run main '{"messages": "Hello, how are you?"}'
```

### Configure in openai_agents.json

```json
{
  "agents": {
    "triage": "samples/triage-agent/main.py:main"
  }
}
```

## Input/Output Models

### Input
```python
class Input(BaseModel):
    messages: str  # User message in any language
```

### Output
```python
class Output(BaseModel):
    response: str       # Agent's response
    agent_used: str     # Which specialist was used
```

## Example Execution

```bash
$ uipath run main '{"messages": "Hola, ¿cómo estás?"}'

Processing message: Hola, ¿cómo estás?
¡Hola! Estoy muy bien, gracias. ¿Y tú, cómo estás?

Agent used: spanish_agent
```

## How It Works

1. **User sends message**: Message can be in any supported language
2. **Triage agent analyzes**: Determines the language of the message
3. **Handoff occurs**: Passes control to the appropriate specialist
4. **Specialist responds**: Answers in their designated language
5. **Response returned**: With both the response and which agent handled it

## Key Features

- **Automatic language detection**: No need to specify language explicitly
- **Streaming responses**: Real-time output as the agent responds
- **Tracing support**: Uses `@traced` decorator for observability
- **Type safety**: Pydantic models for inputs and outputs

## Based On

This example is adapted from the [OpenAI Agents routing pattern](https://github.com/openai/openai-agents-python/blob/main/examples/agent_patterns/routing.py).

## Next Steps

- Add more language specialists
- Implement domain-specific routing (sales, support, technical)
- Combine with tools for enhanced capabilities
- Add conversation history for multi-turn interactions
