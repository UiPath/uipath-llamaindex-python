# Debugging Sample - Breakpoint Debugging with OpenAI Agents

This sample demonstrates how to use breakpoint debugging with UiPath OpenAI Agents. It shows how to pause agent execution at specific points (e.g., before tool calls) and inspect the state before resuming.

## Features

- **Breakpoint Support**: Pause execution at tool calls, handoffs, or other events
- **State Inspection**: Examine agent state when breakpoints are hit
- **Resume Control**: Continue execution after inspection
- **Simple Tools**: Math and weather tools to demonstrate debugging workflow

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

3. Initialize the project:
   ```bash
   uipath init
   ```

## Running the Sample

### With Breakpoints (Interactive Debugging)

Run the debug runner script with breakpoints enabled:

```bash
uv run python debug_runner.py
```

This will:
1. Start the agent with breakpoints enabled on tool calls
2. Pause execution before each tool call
3. Display the current state and breakpoint information
4. Wait for you to press Enter to resume
5. Continue until the next breakpoint or completion

**Example output:**
```
============================================================
Starting agent execution with breakpoints enabled
Breakpoints: tool calls
============================================================

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
BREAKPOINT HIT #1
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Location: tool_called
Type: before

Current state:
{'tool_name': 'calculate_sum', 'arguments': {'a': 5, 'b': 3}}

Press Enter to resume execution...
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

### Without Breakpoints (Normal Execution)

Run without breakpoints for comparison:

```bash
uv run python debug_runner.py --no-breakpoints
```

This runs the agent normally without pausing.

### Using UiPath CLI

You can also run the agent using the standard UiPath CLI:

```bash
# Normal execution (no breakpoints)
uipath run main '{"message": "What is 5 + 3?"}'

# Note: Breakpoints require programmatic usage (see debug_runner.py)
```

## Breakpoint Configuration

### Available Breakpoint Types

Breakpoints use **specific tool/agent names only**, matching LangChain and LlamaIndex:
- **LangChain**: `interrupt_before=["node_name", "another_node"]`
- **LlamaIndex**: Step name filtering

**Specific Tool Names**:
- **`breakpoints=["calculate_sum"]`**: Pause when `calculate_sum` tool is called
- **`breakpoints=["get_weather", "calculate_product"]`**: Pause on these specific tools
- **`breakpoints=["calculate_sum", "calculate_product", "get_weather"]`**: Pause on any of these

**Specific Agent Names** (for handoffs):
- **`breakpoints=["french_agent"]`**: Pause when handing off to `french_agent`
- **`breakpoints=["french_agent", "spanish_agent"]`**: Pause on handoffs to these agents

**Mixed** (tools + agents):
- **`breakpoints=["calculate_sum", "french_agent"]`**: Pause on specific tool AND specific agent

**All Events** (special case):
- **`breakpoints="*"`**: Pause on all significant events (tool calls, handoffs, approvals)

### Resume Event

To control when execution resumes, provide an `asyncio.Event`:

```python
import asyncio
from uipath.runtime import UiPathExecuteOptions

# Create resume event
resume_event = asyncio.Event()

# Configure options
options = UiPathExecuteOptions(
    breakpoints=["tool"],
    resume_event=resume_event,
)

# When ready to resume from a breakpoint, signal the event:
resume_event.set()
```

If no `resume_event` is provided, execution resumes immediately (no actual pause).

## Code Overview

### `main.py`

Defines the agent with three simple tools:
- `calculate_sum(a, b)`: Adds two numbers
- `calculate_product(a, b)`: Multiplies two numbers
- `get_weather(city)`: Gets simulated weather data

### `debug_runner.py`

Demonstrates two execution modes:

1. **`run_with_breakpoints()`**:
   - Enables breakpoints on tool calls
   - Creates a resume event for pause/resume control
   - Waits for user input at each breakpoint
   - Displays breakpoint information and state

2. **`run_without_breakpoints()`**:
   - Runs agent normally without pausing
   - Useful for comparing behavior

## How Breakpoints Work

1. **Streaming Events**: When breakpoints are enabled, the runtime uses `Runner.run_streamed()` to process events one at a time

2. **Event Detection**: Each streaming event is checked against the configured breakpoints

3. **Pause on Match**: When a matching event is detected:
   - A `UiPathBreakpointResult` is yielded
   - Execution waits on the `resume_event` (if provided)
   - The caller can inspect state and decide when to resume

4. **Resume**: When `resume_event.set()` is called, execution continues to the next event

## Integration with Debuggers

To integrate with a debugger or IDE:

1. **Create a resume event**: `resume_event = asyncio.Event()`

2. **Pass it in options**: Include `resume_event` in `UiPathExecuteOptions`

3. **Handle breakpoint events**: When `UiPathBreakpointResult` is received:
   - Display breakpoint information in your UI
   - Show current state
   - Provide controls (Continue, Step Over, etc.)

4. **Resume execution**: Call `resume_event.set()` when user clicks Continue

## Example: Custom Debugger Integration

```python
import asyncio
from uipath.runtime import UiPathExecuteOptions
from uipath.runtime.debug import UiPathBreakpointResult

async def debug_session():
    # Create resume control
    resume_event = asyncio.Event()

    # Configure breakpoints
    options = UiPathExecuteOptions(
        breakpoints=["tool", "handoff"],
        resume_event=resume_event,
    )

    # Execute with breakpoints
    async for event in runtime.stream(input_data, options):
        if isinstance(event, UiPathBreakpointResult):
            # Breakpoint hit!
            print(f"Paused at: {event.breakpoint_node}")
            print(f"State: {event.current_state}")

            # Show UI controls, wait for user action
            await show_debugger_ui(event)

            # User clicked Continue button
            resume_event.set()
```

## Tips for Debugging

1. **Start with tool breakpoints**: Most useful for understanding agent behavior

2. **Inspect state carefully**: The `current_state` contains information about what the agent is about to do

3. **Use logging**: Add print statements in your tools to see when they execute

4. **Compare with/without**: Run both modes to understand the difference

## Next Steps

- Try modifying the tools in `main.py` to add more functionality
- Experiment with different breakpoint configurations
- Integrate breakpoints into your own agent workflows
- Build custom debugging UIs using the breakpoint events

## Troubleshooting

**Breakpoints not triggering?**
- Ensure you're using `runtime.stream()` not `runtime.execute()`
- Check that breakpoint names match supported events
- Verify `resume_event` is provided in options

**Agent hangs at breakpoint?**
- Make sure to call `resume_event.set()` to continue
- Without `resume_event`, execution should auto-resume

**No tools being called?**
- Check your agent instructions
- Try a more specific query that requires tool usage
