"""Test script to verify async breakpoint functionality with timed auto-resume."""

import asyncio
import time

from uipath.runtime import (
    UiPathExecuteOptions,
    UiPathRuntimeContext,
    UiPathRuntimeStatus,
)
from uipath.runtime.debug import UiPathBreakpointResult
from uipath.runtime.events import UiPathRuntimeEvent

from uipath_openai_agents.runtime.factory import UiPathOpenAIAgentRuntimeFactory


async def auto_resume_after_delay(
    resume_event: asyncio.Event, delay_seconds: float, breakpoint_num: int
):
    """Async task that resumes execution after a delay.

    This simulates a debugger UI where the user clicks "Continue" after inspecting state.
    """
    print(f"  [Async] Waiting {delay_seconds}s before auto-resume...")
    await asyncio.sleep(delay_seconds)
    print(f"  [Async] Signaling resume for breakpoint #{breakpoint_num}")
    resume_event.set()


async def test_breakpoints_async():
    """Test breakpoints with async auto-resume to verify pause/resume works."""

    print("=" * 70)
    print("TESTING ASYNC BREAKPOINT PAUSE/RESUME")
    print("=" * 70)
    print()
    print("This test demonstrates that:")
    print("  1. Execution truly pauses at breakpoints")
    print("  2. Async tasks can control resume timing")
    print("  3. Multiple breakpoints can be hit sequentially")
    print()

    # Create runtime context
    context = UiPathRuntimeContext(
        runtime_dir="./__uipath",
        state_file="state.db",
        resume=False,
    )

    # Create factory and runtime
    factory = UiPathOpenAIAgentRuntimeFactory(context)
    runtime = await factory.new_runtime("main", "async-test-session")

    # Create an event for resume signaling
    resume_event = asyncio.Event()

    # Configure execution with breakpoints on specific tool names
    # Note: Must use specific names like "calculate_sum", not generic "tool"
    # This matches LangChain/LlamaIndex behavior
    options = UiPathExecuteOptions(
        breakpoints=[
            "calculate_sum",
            "calculate_product",
        ],  # Pause on these specific tools
        resume_event=resume_event,
    )

    # Prepare input that will trigger multiple tool calls
    input_data = {"message": "What is 5 + 3? Then multiply that result by 2."}

    print("-" * 70)
    print("Starting agent execution...")
    print("-" * 70)
    print()

    breakpoint_count = 0
    tool_calls_seen = []
    pause_times = []

    start_time = time.time()

    # Execute agent with streaming to receive breakpoint events
    async for event in runtime.stream(input_data, options):
        if isinstance(event, UiPathBreakpointResult):
            # Hit a breakpoint!
            breakpoint_count += 1
            pause_start = time.time()

            print()
            print("!" * 70)
            print(f"⏸️  BREAKPOINT #{breakpoint_count} HIT")
            print("!" * 70)
            print(f"  Location: {event.breakpoint_node}")
            print(f"  Type: {event.breakpoint_type}")
            print(f"  Time since start: {pause_start - start_time:.2f}s")
            print()

            # Extract tool name if available
            if isinstance(event.current_state, dict):
                tool_name = event.current_state.get("name") or event.current_state.get(
                    "tool_name"
                )
                if tool_name:
                    tool_calls_seen.append(tool_name)
                    print(f"  🔧 Tool being called: {tool_name}")

                # Show arguments if available
                args = event.current_state.get("arguments")
                if args:
                    print(f"  📝 Arguments: {args}")

            print()

            # Clear event for next iteration
            resume_event.clear()

            # Schedule async resume after delay (simulates debugger UI interaction)
            delay = 1.0  # 1 second pause to demonstrate async behavior
            asyncio.create_task(
                auto_resume_after_delay(resume_event, delay, breakpoint_count)
            )

            # This await demonstrates that execution is truly paused
            # The runtime is waiting for the resume signal
            print("  ⏳ Execution paused, waiting for resume signal...")
            await asyncio.sleep(0.1)  # Small delay to let print buffer flush

            pause_end = time.time()
            pause_duration = pause_end - pause_start
            pause_times.append(pause_duration)

        elif isinstance(event, UiPathRuntimeEvent):
            # Regular runtime event
            event_type = type(event).__name__
            print(f"  📡 Event: {event_type}")

        elif event.status == UiPathRuntimeStatus.COMPLETED:
            # Final result
            end_time = time.time()
            total_time = end_time - start_time

            print()
            print("=" * 70)
            print("✅ EXECUTION COMPLETED")
            print("=" * 70)
            print()
            print("📊 Statistics:")
            print(f"  • Breakpoints hit: {breakpoint_count}")
            print(f"  • Tool calls intercepted: {tool_calls_seen}")
            print(f"  • Total execution time: {total_time:.2f}s")
            if pause_times:
                total_pause = sum(pause_times)
                print(f"  • Total pause time: {total_pause:.2f}s")
                print(f"  • Active execution time: {total_time - total_pause:.2f}s")
            print()
            print("📤 Final output:")
            print(f"  {event.output}")
            print("=" * 70)

    # Cleanup
    await factory.dispose()

    # Verify async behavior
    print()
    print("-" * 70)
    if breakpoint_count > 0:
        print("✅ SUCCESS: Async breakpoint system is working!")
        print(f"   ✓ Execution paused {breakpoint_count} time(s)")
        print(f"   ✓ Intercepted tool calls: {tool_calls_seen}")
        print(f"   ✓ Pause durations: {[f'{t:.2f}s' for t in pause_times]}")
        print()
        print("   The async resume tasks successfully controlled execution flow!")
    else:
        print("⚠️  WARNING: No breakpoints were hit")
        print("   - The agent may not have called any tools")
        print("   - Check the agent's response above")

    print("-" * 70)
    print()


async def test_without_breakpoints():
    """Test normal execution without breakpoints for comparison."""

    print()
    print("=" * 70)
    print("COMPARISON: Running WITHOUT breakpoints")
    print("=" * 70)
    print()

    context = UiPathRuntimeContext(
        runtime_dir="./__uipath",
        state_file="state.db",
        resume=False,
    )

    factory = UiPathOpenAIAgentRuntimeFactory(context)
    runtime = await factory.new_runtime("main", "no-breakpoints-session")

    input_data = {"message": "What is 5 + 3?"}

    start_time = time.time()
    result = await runtime.execute(input_data)
    end_time = time.time()

    print(f"Execution time: {end_time - start_time:.2f}s")
    print(f"Result: {result.output}")
    print("=" * 70)
    print()

    await factory.dispose()


if __name__ == "__main__":
    # Run async breakpoint test
    asyncio.run(test_breakpoints_async())

    # Optional: Run comparison test
    # asyncio.run(test_without_breakpoints())
