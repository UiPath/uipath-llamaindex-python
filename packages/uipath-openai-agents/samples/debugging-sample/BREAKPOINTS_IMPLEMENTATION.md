# Breakpoint Implementation for OpenAI Agents Runtime

This document describes the breakpoint debugging implementation for UiPath OpenAI Agents.

## Overview

Breakpoints allow pausing agent execution at specific points (e.g., before tool calls, handoffs) to inspect state and control execution flow. This is useful for:

- Debugging agent behavior
- Understanding tool usage patterns
- Building step-through debuggers
- Interactive agent development

## Architecture

### Streaming-Based Approach

Unlike hooks-based approaches, this implementation uses OpenAI's `Runner.run_streamed()` API to achieve true pause/resume capability:

1. **Event Streaming**: `Runner.run_streamed()` returns events one at a time
2. **Event Detection**: Each event is checked against configured breakpoints
3. **Pause Mechanism**: When matching event found:
   - Create `UiPathBreakpointResult` with current state
   - Yield result to caller
   - Wait on `resume_event` (asyncio.Event)
4. **Resume**: External debugger calls `resume_event.set()` to continue

### Key Files

#### [runtime.py](../../src/uipath_openai_agents/runtime/runtime.py)

**`_run_agent_streamed()` method** (lines 256-319):
- Uses `Runner.run_streamed()` when breakpoints enabled
- Iterates through stream events
- Pauses at matching events
- Waits for resume signal

**`_should_pause_at_event()` method** (lines 321-371):
- Maps UiPath breakpoint names to OpenAI event names
- Supports `"*"` for all events
- Checks event type and name

**`_create_breakpoint_result_from_event()` method** (lines 373-393):
- Extracts state from streaming event
- Creates `UiPathBreakpointResult` object

**Breakpoint Mapping**:
```python
breakpoint_mapping = {
    "tool": "tool_called",           # Before tool execution
    "handoff": "handoff_requested",   # Before agent handoff
    "approval": "mcp_approval_requested",  # MCP tool approval
}
```

#### [UiPathBreakpointResult](../../../../../uipath-runtime-python/src/uipath/runtime/debug/breakpoint.py)

Result object for suspended execution:
- `status`: Always `SUSPENDED`
- `breakpoint_node`: Event name where paused
- `breakpoint_type`: `"before"` or `"after"`
- `current_state`: Event data (dict)
- `next_nodes`: Nodes that will execute next

## Usage

### Basic Example

```python
import asyncio
from uipath.runtime import UiPathExecuteOptions
from uipath.runtime.debug import UiPathBreakpointResult

# Create resume control
resume_event = asyncio.Event()

# Configure breakpoints
options = UiPathExecuteOptions(
    breakpoints=["tool"],  # Pause before tool calls
    resume_event=resume_event,
)

# Execute with streaming
async for event in runtime.stream(input_data, options):
    if isinstance(event, UiPathBreakpointResult):
        # Breakpoint hit!
        print(f"Paused at: {event.breakpoint_node}")
        print(f"State: {event.current_state}")

        # ... inspect, show UI, etc ...

        # Resume execution
        resume_event.set()
```

### Breakpoint Types

| UiPath Name | OpenAI Event | Description |
|-------------|--------------|-------------|
| `"tool"` | `"tool_called"` | Before tool execution |
| `"handoff"` | `"handoff_requested"` | Before agent handoff |
| `"approval"` | `"mcp_approval_requested"` | MCP tool approval required |
| `"*"` | All above events | Pause on all significant events |

### Resume Event Behavior

**With `resume_event`**:
- Execution waits at breakpoint until `resume_event.set()` is called
- Allows interactive debugging

**Without `resume_event`**:
- `UiPathBreakpointResult` is still yielded
- Execution continues immediately (logging only)
- Useful for breakpoint tracking without pausing

## Implementation Details

### Why Streaming Instead of Hooks?

OpenAI Agents SDK provides `AgentHooks` for lifecycle callbacks, but:

❌ **Hooks can't pause execution**:
- Hooks are fire-and-forget callbacks
- No way to block the agent runner
- Only useful for telemetry/logging

✅ **Streaming enables pause/resume**:
- We control the async iterator
- Can pause iteration at any event
- True debugging capability

### Event Flow

```
Runner.run_streamed()
  ↓
stream_events() iterator
  ↓
_run_agent_streamed() processes each event
  ↓
_should_pause_at_event() checks breakpoints
  ↓ (if match)
_create_breakpoint_result_from_event()
  ↓
Yield UiPathBreakpointResult
  ↓
await resume_event.wait()  ← PAUSED HERE
  ↓
Continue to next event
```

### State Captured at Breakpoints

For `tool_called` events:
```python
{
    "name": "calculate_sum",
    "arguments": {"a": 5, "b": 3},
    "type": "tool_called",
    ...
}
```

For `handoff_requested` events:
```python
{
    "target_agent": "french_agent",
    "source_agent": "triage_agent",
    ...
}
```

## Testing

### Working Samples

✅ **Non-streaming execution** ([main.py](main.py)):
```bash
uv run uipath run main '{"message": "What is 5 + 3?"}'
```
- Tools execute correctly
- No breakpoints (normal flow)

### Breakpoint Testing

The [debug_runner.py](debug_runner.py) and [test_breakpoints.py](test_breakpoints.py) scripts demonstrate breakpoint usage:

- Auto-resume after 3-second timeout
- Shows breakpoint information
- Tracks tool calls intercepted

**Note**: Interactive debugging requires proper async event loop handling.

## Integration Points

### UiPath Debug Bridge

For full debugging integration:

1. **Debugger UI** sends commands via API
2. **Runtime** emits `UiPathBreakpointResult` events
3. **Debugger** displays state and controls
4. **User** clicks Continue → calls `resume_event.set()`
5. **Runtime** resumes execution

### Example Debugger Integration

```python
class DebugController:
    def __init__(self):
        self.resume_event = asyncio.Event()
        self.current_breakpoint = None

    async def on_breakpoint(self, bp_result: UiPathBreakpointResult):
        self.current_breakpoint = bp_result
        # Send to UI
        await self.send_to_ui({
            "type": "breakpoint",
            "node": bp_result.breakpoint_node,
            "state": bp_result.current_state,
        })

    def resume(self):
        """Called by UI when user clicks Continue"""
        self.resume_event.set()
        self.current_breakpoint = None
```

## Limitations

1. **Requires Streaming**: Breakpoints only work with `runtime.stream()`, not `runtime.execute()`
2. **Event Granularity**: Can only pause at event boundaries (not mid-execution)
3. **No Step Over/Into**: Currently only supports Continue (resume)
4. **State is Read-Only**: Cannot modify agent state at breakpoints

## Future Enhancements

- [ ] Step Over/Step Into commands
- [ ] Conditional breakpoints (break if condition met)
- [ ] Breakpoint expressions (evaluate code at breakpoint)
- [ ] State modification (change variables while paused)
- [ ] Breakpoint on specific tool names
- [ ] Watch expressions
- [ ] Call stack inspection

## Comparison with Other Runtimes

| Feature | OpenAI Agents | LangGraph | LlamaIndex |
|---------|---------------|-----------|------------|
| Pause Mechanism | Event streaming | Checkpoint system | Workflow events |
| State Inspection | Event data | Full graph state | Workflow context |
| Resume Control | asyncio.Event | Runner control | Event handlers |
| Granularity | Event-level | Node-level | Step-level |

## References

- [OpenAI Agents SDK Streaming](https://openai.github.io/openai-agents-python/streaming/)
- [UiPath Runtime Debug API](../../../../../uipath-runtime-python/src/uipath/runtime/debug/)
- [Sample Implementation](main.py)
