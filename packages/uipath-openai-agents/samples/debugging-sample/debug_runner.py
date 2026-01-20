"""Example of running an agent with breakpoint debugging.

This script demonstrates how to:
1. Enable breakpoints on specific events (tool calls, handoffs, etc.)
2. Pause execution when breakpoints are hit
3. Resume execution after inspecting state
"""

import asyncio
import sys

from uipath.runtime import (
    UiPathExecuteOptions,
    UiPathRuntimeContext,
    UiPathRuntimeStatus,
)
from uipath.runtime.debug import UiPathBreakpointResult
from uipath.runtime.events import UiPathRuntimeEvent

from uipath_openai_agents.runtime.factory import UiPathOpenAIAgentRuntimeFactory


async def run_with_breakpoints():
    """Run agent with breakpoints enabled."""

    # Create runtime context
    context = UiPathRuntimeContext(
        runtime_dir="./__uipath",
        state_file="state.db",
        resume=False,
    )

    # Create factory and runtime
    factory = UiPathOpenAIAgentRuntimeFactory(context)
    runtime = await factory.new_runtime("main", "debug-session")

    # Create an event for resume signaling
    resume_event = asyncio.Event()

    # Configure execution with breakpoints on specific names
    # Must use actual tool/agent names (like LangChain/LlamaIndex)
    # Examples:
    # - breakpoints=["calculate_sum"]: Pause only on this tool
    # - breakpoints=["french_agent"]: Pause only on handoff to this agent
    # - breakpoints=["calculate_sum", "get_weather"]: Pause on multiple
    # - breakpoints="*": Pause on all events (special case)
    options = UiPathExecuteOptions(
        breakpoints=[
            "calculate_sum",
            "calculate_product",
            "get_weather",
        ],  # Specific tool names
        resume_event=resume_event,  # Event to signal resume
    )

    # Prepare input
    input_data = {
        "message": "What is 5 + 3? Then multiply that result by 2. Also, what's the weather in Tokyo?"
    }

    print("=" * 60)
    print("Starting agent execution with breakpoints enabled")
    print("Breakpoints: calculate_sum, calculate_product, get_weather")
    print("=" * 60)
    print()

    breakpoint_count = 0
    tool_calls_seen = []

    # Execute agent with streaming to receive breakpoint events
    async for event in runtime.stream(input_data, options):
        if isinstance(event, UiPathBreakpointResult):
            # Hit a breakpoint!
            breakpoint_count += 1
            print()
            print("!" * 60)
            print(f"BREAKPOINT HIT #{breakpoint_count}")
            print("!" * 60)
            print(f"Location: {event.breakpoint_node}")
            print(f"Type: {event.breakpoint_type}")
            print()
            print("Current state:")
            print(event.current_state)
            print()

            # Extract tool name if available
            if isinstance(event.current_state, dict):
                tool_name = event.current_state.get("name") or event.current_state.get(
                    "tool_name"
                )
                if tool_name:
                    tool_calls_seen.append(tool_name)
                    print(f"Tool being called: {tool_name}")

            # Create task to wait for user input with timeout
            print("Press Enter to resume (or auto-resume in 3 seconds)...")
            print("!" * 60)

            try:
                # Wait for either user input OR timeout (whichever comes first)
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, input),
                    timeout=3.0,
                )
            except asyncio.TimeoutError:
                print("\n[Auto-resuming after timeout]")

            # Signal resume
            resume_event.set()
            print()
            print("Resuming execution...")
            print()

        elif isinstance(event, UiPathRuntimeEvent):
            # Regular runtime event (if streaming is enabled)
            print(f"Event: {type(event).__name__}")

        elif event.status == UiPathRuntimeStatus.COMPLETED:
            # Final result
            print()
            print("=" * 60)
            print("EXECUTION COMPLETED")
            print("=" * 60)
            print(f"✓ Hit {breakpoint_count} breakpoint(s)")
            if tool_calls_seen:
                print(f"✓ Tool calls intercepted: {tool_calls_seen}")
            print()
            print("Final output:")
            print(event.output)
            print("=" * 60)

    # Cleanup
    await factory.dispose()


async def run_without_breakpoints():
    """Run agent without breakpoints for comparison."""

    # Create runtime context
    context = UiPathRuntimeContext(
        runtime_dir="./__uipath",
        state_file="state.db",
        resume=False,
    )

    # Create factory and runtime
    factory = UiPathOpenAIAgentRuntimeFactory(context)
    runtime = await factory.new_runtime("main", "normal-session")

    # Prepare input
    input_data = {"message": "What is 5 + 3?"}

    print("=" * 60)
    print("Running agent WITHOUT breakpoints (for comparison)")
    print("=" * 60)
    print()

    # Execute agent normally
    result = await runtime.execute(input_data)

    print()
    print("Result:")
    print(result.output)
    print("=" * 60)

    # Cleanup
    await factory.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--no-breakpoints":
        asyncio.run(run_without_breakpoints())
    else:
        asyncio.run(run_with_breakpoints())
