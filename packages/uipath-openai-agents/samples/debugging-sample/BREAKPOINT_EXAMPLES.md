# Breakpoint Configuration Examples

This guide shows all the ways you can configure breakpoints in OpenAI Agents runtime.

## Quick Reference

```python
from uipath.runtime import UiPathExecuteOptions
import asyncio

resume_event = asyncio.Event()

# Generic types
options = UiPathExecuteOptions(
    breakpoints=["tool"],  # All tool calls
    resume_event=resume_event,
)

# Specific names
options = UiPathExecuteOptions(
    breakpoints=["calculate_sum"],  # Only this tool
    resume_event=resume_event,
)

# Combined
options = UiPathExecuteOptions(
    breakpoints=["tool", "french_agent"],  # All tools + specific agent
    resume_event=resume_event,
)
```

## Generic Event Types

### All Tool Calls

Pause before **every** tool execution:

```python
options = UiPathExecuteOptions(
    breakpoints=["tool"],
    resume_event=resume_event,
)
```

**When it pauses**:
- `calculate_sum(5, 3)` → ⏸️ PAUSE
- `calculate_product(8, 2)` → ⏸️ PAUSE
- `get_weather("Tokyo")` → ⏸️ PAUSE

### All Agent Handoffs

Pause before **every** agent handoff:

```python
options = UiPathExecuteOptions(
    breakpoints=["handoff"],
    resume_event=resume_event,
)
```

**When it pauses**:
- Handoff to `french_agent` → ⏸️ PAUSE
- Handoff to `spanish_agent` → ⏸️ PAUSE
- Handoff to `english_agent` → ⏸️ PAUSE

### All MCP Approval Requests

```python
options = UiPathExecuteOptions(
    breakpoints=["approval"],
    resume_event=resume_event,
)
```

### All Events

Pause on all supported event types:

```python
options = UiPathExecuteOptions(
    breakpoints="*",  # String, not list!
    resume_event=resume_event,
)
```

## Specific Names

### Single Specific Tool

Pause **only** when `calculate_sum` is called:

```python
options = UiPathExecuteOptions(
    breakpoints=["calculate_sum"],
    resume_event=resume_event,
)
```

**When it pauses**:
- `calculate_sum(5, 3)` → ⏸️ PAUSE
- `calculate_product(8, 2)` → ✓ continues
- `get_weather("Tokyo")` → ✓ continues

### Multiple Specific Tools

Pause on **any** of these tools:

```python
options = UiPathExecuteOptions(
    breakpoints=["calculate_sum", "get_weather"],
    resume_event=resume_event,
)
```

**When it pauses**:
- `calculate_sum(5, 3)` → ⏸️ PAUSE
- `calculate_product(8, 2)` → ✓ continues
- `get_weather("Tokyo")` → ⏸️ PAUSE

### Specific Agent Handoff

Pause **only** when handing off to `french_agent`:

```python
options = UiPathExecuteOptions(
    breakpoints=["french_agent"],
    resume_event=resume_event,
)
```

**When it pauses**:
- Handoff to `french_agent` → ⏸️ PAUSE
- Handoff to `spanish_agent` → ✓ continues
- Handoff to `english_agent` → ✓ continues

## Combined Configurations

### All Tools + Specific Tool

This is redundant but allowed:

```python
options = UiPathExecuteOptions(
    breakpoints=["tool", "calculate_sum"],  # "tool" already catches calculate_sum
    resume_event=resume_event,
)
```

Effectively the same as `breakpoints=["tool"]`.

### All Handoffs + Specific Agent

```python
options = UiPathExecuteOptions(
    breakpoints=["handoff", "french_agent"],
    resume_event=resume_event,
)
```

Effectively the same as `breakpoints=["handoff"]`.

### Mixed: Generic + Specific

```python
options = UiPathExecuteOptions(
    breakpoints=["tool", "french_agent"],  # Tools + specific agent
    resume_event=resume_event,
)
```

**When it pauses**:
- ANY tool call → ⏸️ PAUSE
- Handoff to `french_agent` → ⏸️ PAUSE
- Handoff to `spanish_agent` → ✓ continues

### Multiple Specifics from Different Categories

```python
options = UiPathExecuteOptions(
    breakpoints=["calculate_sum", "french_agent", "get_weather"],
    resume_event=resume_event,
)
```

**When it pauses**:
- `calculate_sum(...)` → ⏸️ PAUSE
- `get_weather(...)` → ⏸️ PAUSE
- `calculate_product(...)` → ✓ continues
- Handoff to `french_agent` → ⏸️ PAUSE
- Handoff to `spanish_agent` → ✓ continues

## Comparison with Other Runtimes

### LangChain (LangGraph)

```python
# LangChain uses interrupt_before with node names
graph.ainvoke(
    input_data,
    config,
    interrupt_before=["my_agent_node", "tool_node"],
)
```

**Our equivalent**:
```python
options = UiPathExecuteOptions(
    breakpoints=["my_tool", "my_agent"],
)
```

### LlamaIndex (Workflows)

```python
# LlamaIndex filters by step name
if event.breakpoint_node in active_breakpoints:
    # Pause
```

**Our equivalent**:
```python
options = UiPathExecuteOptions(
    breakpoints=["step_name", "another_step"],
)
```

## Advanced: Conditional Breakpoints

Currently not supported, but you can implement similar logic:

```python
async for event in runtime.stream(input_data, options):
    if isinstance(event, UiPathBreakpointResult):
        # Custom logic
        if event.current_state.get("arguments", {}).get("a") > 10:
            # Only pause if 'a' argument is greater than 10
            await resume_event.wait()
        else:
            # Auto-resume for small values
            resume_event.set()
```

## Testing Your Breakpoints

### Test 1: Verify Specific Tool

```bash
# Should pause ONLY on calculate_sum
uv run python test_specific_tools.py
```

Expected output:
```
⏸️  BREAKPOINT: Paused on tool 'calculate_sum'
Calculating: 5 + 3 = 8
✓ continues without pause
Calculating: 8 * 2 = 16
✅ SUCCESS: Only calculate_sum was paused!
```

### Test 2: Verify All Tools

Modify test to use `breakpoints=["tool"]` - should pause on ALL tools.

### Test 3: Verify No Breakpoints

Remove `breakpoints` option - should run without any pauses.

## Troubleshooting

**Breakpoint not triggering?**
- Check spelling: tool names are case-sensitive
- Verify the tool is actually being called (check agent output)
- Ensure you're using `runtime.stream()` not `runtime.execute()`

**Too many breakpoints?**
- Use specific names instead of generic types
- Example: Replace `["tool"]` with `["calculate_sum"]`

**Agent hangs forever?**
- Make sure to call `resume_event.set()` after each breakpoint
- Check that your async event loop is running

## Best Practices

1. **Start generic, then narrow down**: Begin with `["tool"]` to see all tool calls, then switch to specific names
2. **Use specific names in production**: More predictable behavior
3. **Always provide resume_event**: Otherwise you can't actually pause
4. **Log breakpoint hits**: Track which breakpoints are being hit
5. **Test without breakpoints first**: Ensure agent works before adding debugging

## See Also

- [README.md](README.md) - Full documentation
- [BREAKPOINTS_IMPLEMENTATION.md](BREAKPOINTS_IMPLEMENTATION.md) - Technical details
- [test_specific_tools.py](test_specific_tools.py) - Test suite
