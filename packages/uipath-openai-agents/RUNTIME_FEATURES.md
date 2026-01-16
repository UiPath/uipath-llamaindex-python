# OpenAI Agents Runtime Features

This document describes the runtime features implemented for the UiPath OpenAI Agents integration, inspired by the UiPath LlamaIndex runtime.

## Implemented Features

### 1. Enhanced Error Handling ✅ (CRITICAL)

Structured error handling with specific error codes and categories for better diagnostics and debugging.

**Files:**
- `src/uipath_openai_agents/runtime/errors.py` - Error codes and exception classes

**Error Codes:**
```python
class UiPathOpenAIAgentsErrorCode(Enum):
    AGENT_EXECUTION_FAILURE = "AGENT_EXECUTION_FAILURE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    SERIALIZE_OUTPUT_ERROR = "SERIALIZE_OUTPUT_ERROR"
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_TYPE_ERROR = "AGENT_TYPE_ERROR"
    AGENT_VALUE_ERROR = "AGENT_VALUE_ERROR"
    AGENT_LOAD_ERROR = "AGENT_LOAD_ERROR"
    AGENT_IMPORT_ERROR = "AGENT_IMPORT_ERROR"
```

**Usage Example:**
```python
from uipath_openai_agents.runtime.errors import (
    UiPathOpenAIAgentsErrorCode,
    UiPathOpenAIAgentsRuntimeError,
)

# Raise structured error
raise UiPathOpenAIAgentsRuntimeError(
    code=UiPathOpenAIAgentsErrorCode.AGENT_EXECUTION_FAILURE,
    title="Agent execution failed",
    detail="Detailed error message here",
    category=UiPathErrorCategory.USER,
)
```

### 2. Storage & State Persistence ✅ (CRITICAL)

SQLite-based storage for agent sessions, resume triggers, and key-value data.

**Files:**
- `src/uipath_openai_agents/runtime/storage.py` - Storage implementation
- `src/uipath_openai_agents/runtime/_sqlite.py` - Async SQLite wrapper

**Features:**
- Agent state save/load
- Resume trigger management
- Key-value storage scoped by runtime_id and namespace
- Automatic database setup with proper indexes
- WAL mode for optimal concurrency

**Usage Example:**
```python
from uipath_openai_agents.runtime.storage import SqliteAgentStorage

# Create storage
storage = SqliteAgentStorage("path/to/storage.db")
await storage.setup()

# Save agent state
runtime_id = "my_agent_123"
state = {"step": "processing", "data": {...}}
await storage.save_state(runtime_id, state)

# Load agent state
loaded_state = await storage.load_state(runtime_id)

# Key-value operations
await storage.set_value(runtime_id, "namespace", "key", "value")
value = await storage.get_value(runtime_id, "namespace", "key")

await storage.dispose()
```

### 3. Breakpoint Support ✅ (CRITICAL)

Infrastructure for debugging agents with breakpoint events.

**Files:**
- `src/uipath_openai_agents/runtime/breakpoints.py` - Breakpoint events and utilities

**Features:**
- `BreakpointEvent` for pause notifications
- `BreakpointResumeEvent` for resuming execution
- `supports_breakpoints()` capability detection

**Note:** Full breakpoint support is limited by OpenAI Agents SDK's execution model. Currently provides foundation for:
- Agent execution boundaries
- Future: Tool call breakpoints
- Future: Handoff breakpoints

**Usage Example:**
```python
from uipath_openai_agents.runtime.breakpoints import (
    BreakpointEvent,
    BreakpointResumeEvent,
    supports_breakpoints,
)

# Check if agent supports breakpoints
if supports_breakpoints(agent):
    # Breakpoint logic here
    pass
```

### 4. Improved Serialization ✅

Centralized output serialization for consistent handling across all runtime operations.

**Files:**
- `src/uipath_openai_agents/runtime/_serialize.py` - Serialization utilities

**Features:**
- Pydantic model serialization
- Dictionary and list recursion
- Enum value extraction
- Fallback handling

**Usage Example:**
```python
from uipath_openai_agents.runtime._serialize import serialize_output

# Serialize any output
serialized = serialize_output(agent_output)
# Handles Pydantic models, dicts, lists, enums automatically
```

### 5. Runtime Integration ✅

All features integrated into runtime and factory classes.

**Files:**
- `src/uipath_openai_agents/runtime/runtime.py` - Runtime with storage support
- `src/uipath_openai_agents/runtime/factory.py` - Factory with storage creation
- `src/uipath_openai_agents/runtime/agent.py` - Agent loader with error handling

**Usage Example:**
```python
from uipath_openai_agents.runtime import UiPathOpenAIAgentRuntime
from uipath_openai_agents.runtime.storage import SqliteAgentStorage

# Create storage
storage = SqliteAgentStorage("storage.db")
await storage.setup()

# Create runtime with storage
runtime = UiPathOpenAIAgentRuntime(
    agent=my_agent,
    runtime_id="unique_id",
    storage=storage,
    debug_mode=True,
)

# Execute agent
result = await runtime.execute({"message": "Hello"})

# Stream events
async for event in runtime.stream({"message": "Hello"}):
    print(event)
```

## Cleanup & Resource Management ✅

Proper disposal of resources to prevent event loop errors:

**Runtime Disposal:**
```python
runtime = UiPathOpenAIAgentRuntime(...)
try:
    result = await runtime.execute({"message": "Hello"})
finally:
    await runtime.dispose()  # Properly closes storage and sessions
```

**Features:**
- Storage disposed before event loop closes
- Pending aiosqlite transactions committed
- Best-effort error handling in cleanup paths
- No asyncio event loop errors during `uipath init`

**Files:**
- `src/uipath_openai_agents/runtime/runtime.py:323-334` - Runtime disposal
- `src/uipath_openai_agents/runtime/_sqlite.py:57-72` - SQLite cleanup

## Test Coverage

All features are covered by comprehensive tests:

```bash
# Run all tests
uv run pytest tests/ -v

# Test results:
# - 14 tests passed
# - Error handling: ✅
# - Schema extraction: ✅
# - Storage operations: ✅
# - Runtime initialization: ✅
# - Pydantic models: ✅
# - Resource disposal: ✅
```

**Test Files:**
- `tests/test_integration.py` - Integration tests for new features
- `tests/test_agent_as_tools_schema.py` - Schema extraction tests
- `tests/test_schema_inference.py` - Parameter inference tests

## Validation

All code passes type checking and linting:

```bash
# Type checking
uv run mypy src/uipath_openai_agents
# Result: Success - no issues found

# Linting
uv run ruff check src/uipath_openai_agents
# Result: All checks passed
```

## Dependencies

New dependency added:
- `aiosqlite>=0.20.0` - Async SQLite support

## Architecture Alignment

The implementation closely mirrors the LlamaIndex runtime:

| Feature | LlamaIndex | OpenAI Agents | Status |
|---------|-----------|---------------|--------|
| Structured Errors | ✅ | ✅ | Implemented |
| Storage Layer | ✅ | ✅ | Implemented |
| Breakpoints | ✅ | ⚠️ Limited | Infrastructure ready |
| Context Management | ✅ | ✅ | Uses SQLiteSession |
| Event Streaming | ✅ | ✅ | Implemented |
| Serialization | ✅ | ✅ | Implemented |

**Key Differences:**
- OpenAI Agents use `Runner.run()` (less granular than LlamaIndex workflow steps)
- Breakpoints limited to agent execution boundaries
- Context management uses OpenAI SDK's `SQLiteSession`

## Future Enhancements

Potential improvements:
1. **Richer Breakpoints**: Tool call and handoff breakpoints
2. **Enhanced Event Streaming**: More granular event types
3. **Suspended State Handling**: Human-in-the-loop patterns
4. **Resume Trigger Management**: External orchestration support
5. **Telemetry Normalization**: Better observability

## Examples

See the agent-as-tools sample for a complete example:
- `samples/agent-as-tools/main.py` - Full implementation
- `samples/agent-as-tools/README.md` - Documentation
