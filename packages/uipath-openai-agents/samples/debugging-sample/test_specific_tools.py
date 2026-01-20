"""Test script demonstrating specific tool name breakpoints."""

import asyncio

from uipath.runtime import (
    UiPathExecuteOptions,
    UiPathRuntimeContext,
    UiPathRuntimeStatus,
)
from uipath.runtime.debug import UiPathBreakpointResult

from uipath_openai_agents.runtime.factory import UiPathOpenAIAgentRuntimeFactory


async def test_specific_tool_breakpoint():
    """Test breakpoints on specific tool names."""

    print("=" * 70)
    print("TESTING SPECIFIC TOOL NAME BREAKPOINTS")
    print("=" * 70)
    print()
    print("This test demonstrates:")
    print("  • Breaking only on specific tool calls (e.g., 'calculate_sum')")
    print("  • Other tools execute without pausing")
    print()

    # Create runtime context
    context = UiPathRuntimeContext(
        runtime_dir="./__uipath",
        state_file="state.db",
        resume=False,
    )

    # Create factory and runtime
    factory = UiPathOpenAIAgentRuntimeFactory(context)
    runtime = await factory.new_runtime("main", "specific-tool-test")

    # Create resume event
    resume_event = asyncio.Event()

    # Configure breakpoints for ONLY calculate_sum (not calculate_product)
    options = UiPathExecuteOptions(
        breakpoints=["calculate_sum"],  # Only pause on this specific tool!
        resume_event=resume_event,
    )

    # This will call both calculate_sum AND calculate_product
    input_data = {"message": "What is 5 + 3? Then multiply that result by 2."}

    print("-" * 70)
    print("Breakpoints configured for: calculate_sum only")
    print("Expected: Pause on calculate_sum, skip calculate_product")
    print("-" * 70)
    print()

    breakpoints_hit = []

    async for event in runtime.stream(input_data, options):
        if isinstance(event, UiPathBreakpointResult):
            # Extract tool name
            tool_name = None
            if isinstance(event.current_state, dict):
                tool_name = event.current_state.get("name")

            breakpoints_hit.append(tool_name)

            print(f"⏸️  BREAKPOINT: Paused on tool '{tool_name}'")
            print(f"   State: {event.current_state}")
            print("   → Auto-resuming...")
            print()

            # Auto-resume
            resume_event.clear()
            resume_event.set()

        elif event.status == UiPathRuntimeStatus.COMPLETED:
            print("=" * 70)
            print("✅ EXECUTION COMPLETED")
            print("=" * 70)
            print(f"Breakpoints hit: {breakpoints_hit}")
            print()
            if breakpoints_hit == ["calculate_sum"]:
                print("✅ SUCCESS: Only calculate_sum was paused!")
                print("   calculate_product executed without pausing")
            else:
                print(f"⚠️  Unexpected breakpoints: {breakpoints_hit}")
            print()
            print(f"Final output: {event.output}")
            print("=" * 70)

    await factory.dispose()


async def test_multiple_specific_tools():
    """Test breakpoints on multiple specific tools."""

    print()
    print("=" * 70)
    print("TESTING MULTIPLE SPECIFIC TOOL BREAKPOINTS")
    print("=" * 70)
    print()

    context = UiPathRuntimeContext(
        runtime_dir="./__uipath",
        state_file="state.db",
        resume=False,
    )

    factory = UiPathOpenAIAgentRuntimeFactory(context)
    runtime = await factory.new_runtime("main", "multi-tool-test")

    resume_event = asyncio.Event()

    # Pause on BOTH calculate_sum AND get_weather
    options = UiPathExecuteOptions(
        breakpoints=["calculate_sum", "get_weather"],
        resume_event=resume_event,
    )

    # Query that uses sum and weather (but not product)
    input_data = {"message": "What is 5 + 3? Also, what's the weather in Tokyo?"}

    print("Breakpoints configured for: calculate_sum, get_weather")
    print("Expected: Pause on both")
    print("-" * 70)
    print()

    breakpoints_hit = []

    async for event in runtime.stream(input_data, options):
        if isinstance(event, UiPathBreakpointResult):
            tool_name = None
            if isinstance(event.current_state, dict):
                tool_name = event.current_state.get("name")

            breakpoints_hit.append(tool_name)

            print(f"⏸️  BREAKPOINT #{len(breakpoints_hit)}: Paused on '{tool_name}'")
            print()

            resume_event.clear()
            resume_event.set()

        elif event.status == UiPathRuntimeStatus.COMPLETED:
            print("=" * 70)
            print("✅ EXECUTION COMPLETED")
            print("=" * 70)
            print(f"Breakpoints hit: {breakpoints_hit}")
            print()
            if set(breakpoints_hit) == {"calculate_sum", "get_weather"}:
                print("✅ SUCCESS: Both specific tools were paused!")
            else:
                print(f"Result: {breakpoints_hit}")
            print("=" * 70)

    await factory.dispose()


if __name__ == "__main__":
    # Test 1: Single specific tool
    asyncio.run(test_specific_tool_breakpoint())

    # Test 2: Multiple specific tools
    # asyncio.run(test_multiple_specific_tools())
