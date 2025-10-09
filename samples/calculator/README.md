# Calculator Agent Sample

A simple LlamaIndex agent that performs basic mathematical operations using function tools.

## Features

- **Add** two numbers
- **Multiply** two numbers

## Setup

1. **Install dependencies:**

   ```bash
   uv pip install -e .
   ```

2. **Authenticate with UiPath:**

   ```bash
   uv run uipath auth
   ```

   This will open a browser for authentication and create a `.env` file with your credentials.

## Usage

### Interactive Development Mode

```bash
uv run uipath dev
```

Then you can chat with the calculator agent interactively:
- "What is 25 times 4?"
- "Add 42 and 58"

### Direct Execution

```bash
uv run uipath run agent '{"query": "What is 25 times 4?"}'
```

## How It Works

The agent uses LlamaIndex's `FunctionAgent` with two simple calculator tools:
- Each Python function is automatically converted into a tool the LLM can call
- The agent analyzes your question and determines which tool(s) to use
- It executes the appropriate calculations and returns a natural language response

## Files

- `main.py` - Agent definition with calculator tools
- `llama_index.json` - Workflow configuration mapping
- `pyproject.toml` - Python project dependencies
- `uipath.json` - Entry point schema for UiPath platform
- `.env.example` - Example environment variables (copy to `.env`)

