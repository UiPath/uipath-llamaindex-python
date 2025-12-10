import logging
from typing import Any, Callable, Optional

from llama_index.core.llms import LLM, ChatMessage, MessageRole
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import StartEvent, StopEvent, Workflow, step
from pydantic import BaseModel, Field

from uipath_llamaindex.llms import UiPathOpenAI
from uipath_llamaindex.llms.bedrock import UiPathChatBedrock, UiPathChatBedrockConverse
from uipath_llamaindex.llms.vertex import UiPathVertex

logger = logging.getLogger(__name__)

# Methods to skip for specific models due to known limitations
SKIP_METHODS: dict[str, set[str]] = {
    "UiPathChatBedrock": {
        "tool_calling",  # Bedrock LLMs do not support tool calling - use BedrockConverse instead
    },
}


def create_test_models(max_tokens: int = 100) -> list[tuple[str, LLM]]:
    """Create all test chat models with the specified max_tokens."""
    return [
        (
            "UiPathOpenAI",
            UiPathOpenAI(
                temperature=0.7,
                max_tokens=max_tokens,
                max_retries=0,
            ),
        ),
        (
            "UiPathChatBedrockConverse",
            UiPathChatBedrockConverse(
                temperature=0.7,
                max_tokens=max_tokens,
                max_retries=1,
            ),
        ),
        (
            "UiPathChatBedrock",
            UiPathChatBedrock(
                temperature=0.7,
                max_tokens=max_tokens,
                max_retries=1,
            ),
        ),
        (
            "UiPathVertex",
            UiPathVertex(
                temperature=0.7,
                max_tokens=max_tokens,
            ),
        ),
    ]


def format_error_message(error: str, max_length: int = 60) -> str:
    """Format an error message, truncating if too long."""
    error_str = str(error)
    if len(error_str) > max_length:
        return f"{error_str[:max_length]}..."
    return error_str


def get_weather(location: str, unit: str = "celsius") -> str:
    """Get the current weather for a location.

    Args:
        location: The city and state/country, e.g. 'San Francisco, CA'
        unit: Temperature unit (celsius or fahrenheit)
    """
    return f"The weather in {location} is 72°{unit[0].upper()}"


def calculate(expression: str) -> str:
    """Calculate a mathematical expression.

    Args:
        expression: A mathematical expression to evaluate, e.g. '2 + 2'
    """
    try:
        result = eval(expression)
        return f"The result is {result}"
    except Exception as e:
        return f"Error calculating: {e}"


class PersonInfo(BaseModel):
    """Information about a person."""

    name: str = Field(description="The person's full name")
    age: int = Field(description="The person's age in years")
    city: str = Field(description="The city where the person lives")


class TestResult:
    """Accumulates test metrics across all test runs."""

    def __init__(self):
        self.chunks = 0
        self.content_length = 0
        self.tool_calls = 0

    def add_response(self, response: Any) -> None:
        if hasattr(response, "message") and hasattr(response.message, "content"):
            if response.message.content:
                self.content_length += len(response.message.content)
        elif hasattr(response, "text") and response.text:
            self.content_length += len(response.text)
        elif hasattr(response, "content") and response.content:
            self.content_length += len(str(response.content))

    def add_chunks(self, count: int) -> None:
        self.chunks += count

    def add_tool_calls(self, count: int) -> None:
        self.tool_calls += count


class TestInput(StartEvent):
    """Input event for the test workflow."""

    prompt: str = Field(
        default="Count from 1 to 5.", description="The prompt to send to the LLM"
    )


class TestOutput(StopEvent):
    """Output event for the test workflow."""

    success: bool
    result_summary: str
    chunks_received: int
    content_length: int
    tool_calls_count: int


async def run_test_method(
    method: Callable,
    input_data: Any,
    is_async: bool,
    is_streaming: bool,
    result: TestResult,
) -> Optional[str]:
    """Run a test method and return error message if failed, None if success."""
    try:
        if is_streaming:
            chunks = []
            if is_async:
                async for chunk in await method(input_data):
                    chunks.append(chunk)
            else:
                for chunk in method(input_data):
                    chunks.append(chunk)
            result.add_chunks(len(chunks))
        else:
            if is_async:
                response = await method(input_data)
            else:
                response = method(input_data)
            result.add_response(response)
        return None
    except Exception as e:
        return str(e)


async def test_single_model_all(
    name: str,
    model: LLM,
    prompt: str,
    messages: list[ChatMessage],
    tools: list[FunctionTool],
    tool_prompt: str,
    structured_prompt: str,
) -> tuple[str, dict, TestResult]:
    """Run all tests (complete, chat, stream, tools, structured output) for a single model."""
    logger.info(f"\nTesting {name}...")
    model_results = {}
    result = TestResult()

    # Get methods to skip for this model
    skip_methods = SKIP_METHODS.get(name, set())

    # Test complete/acomplete/stream_complete/astream_complete
    test_methods = [
        ("complete", False, False),
        ("acomplete", True, False),
        ("stream_complete", False, True),
        ("astream_complete", True, True),
    ]

    for method_name, is_async, is_streaming in test_methods:
        if method_name in skip_methods:
            logger.info(f"  Skipping {method_name} (known limitation)")
            model_results[method_name] = "⊘ Skipped (known limitation)"
            continue
        logger.info(f"  Testing {method_name}...")
        try:
            method = getattr(model, method_name)
            error = await run_test_method(
                method, prompt, is_async, is_streaming, result
            )
            if error:
                logger.error(f"     {method_name} failed: {error}")
                model_results[method_name] = f"✗ {format_error_message(error)}"
            else:
                logger.info(f"     {method_name}: ✓")
                model_results[method_name] = "✓"
        except AttributeError:
            logger.warning(f"     {method_name} not available")
            model_results[method_name] = "⊘ Not available"

    # Test chat/achat/stream_chat/astream_chat
    chat_test_methods = [
        ("chat", False, False),
        ("achat", True, False),
        ("stream_chat", False, True),
        ("astream_chat", True, True),
    ]

    for method_name, is_async, is_streaming in chat_test_methods:
        if method_name in skip_methods:
            logger.info(f"  Skipping {method_name} (known limitation)")
            model_results[method_name] = "⊘ Skipped (known limitation)"
            continue
        logger.info(f"  Testing {method_name}...")
        try:
            method = getattr(model, method_name)
            error = await run_test_method(
                method, messages, is_async, is_streaming, result
            )
            if error:
                logger.error(f"     {method_name} failed: {error}")
                model_results[method_name] = f"✗ {format_error_message(error)}"
            else:
                logger.info(f"     {method_name}: ✓")
                model_results[method_name] = "✓"
        except AttributeError:
            logger.warning(f"     {method_name} not available")
            model_results[method_name] = "⊘ Not available"

    # Test tool calling with predict_and_call
    if "tool_calling" in skip_methods:
        logger.info("  Skipping tool_calling (known limitation)")
        model_results["tool_calling"] = "⊘ Skipped (known limitation)"
    else:
        logger.info("  Testing tool_calling...")
        try:
            if hasattr(model, "apredict_and_call"):
                response = await model.apredict_and_call(
                    tools, user_msg=tool_prompt, allow_parallel_tool_calls=True
                )

                if response and hasattr(response, "sources") and response.sources:
                    tool_calls_count = len(response.sources)
                    result.add_tool_calls(tool_calls_count)
                    logger.info(f"     Tool calls detected: {tool_calls_count}")
                    model_results["tool_calling"] = f"✓ ({tool_calls_count} calls)"
                else:
                    logger.warning("     No tool calls detected")
                    model_results["tool_calling"] = "✗ No tool calls detected"
            else:
                logger.warning("     Tool calling not available")
                model_results["tool_calling"] = "⊘ Not available"
        except Exception as e:
            logger.error(f"     Tool calling failed: {e}")
            model_results["tool_calling"] = f"✗ {format_error_message(str(e))}"

    # Test structured output
    if "structured_output" in skip_methods:
        logger.info("  Skipping structured_output (known limitation)")
        model_results["structured_output"] = "⊘ Skipped (known limitation)"
    else:
        logger.info("  Testing structured_output...")
        try:
            if hasattr(model, "as_structured_llm"):
                sllm = model.as_structured_llm(PersonInfo)
                response = await sllm.acomplete(structured_prompt)

                if hasattr(response, "raw") and isinstance(response.raw, PersonInfo):
                    logger.info(
                        f"     Structured output received: {response.raw.model_dump()}"
                    )
                    model_results["structured_output"] = "✓"
                elif isinstance(response, PersonInfo):
                    logger.info(
                        f"     Structured output received: {response.model_dump()}"
                    )
                    model_results["structured_output"] = "✓"
                else:
                    logger.warning(f"     Response is not PersonInfo: {type(response)}")
                    model_results["structured_output"] = (
                        f"✗ Wrong type: {type(response)}"
                    )
            else:
                logger.warning("     Structured output not available")
                model_results["structured_output"] = "⊘ Not available"
        except Exception as e:
            logger.error(f"     Structured output failed: {e}")
            model_results["structured_output"] = f"✗ {format_error_message(str(e))}"

    return name, model_results, result


class ChatModelTestFlow(Workflow):
    """LlamaIndex Workflow for testing chat models."""

    @step
    async def run_tests(self, ev: TestInput) -> TestOutput:
        """Run all tests for all chat models."""
        import asyncio

        logger.info("=" * 80)
        logger.info("Running All Tests")
        logger.info("=" * 80)
        logger.info(f"Prompt: {ev.prompt}")

        models = create_test_models(max_tokens=2000)

        # Create tools
        weather_tool = FunctionTool.from_defaults(fn=get_weather)
        calc_tool = FunctionTool.from_defaults(fn=calculate)
        tools = [weather_tool, calc_tool]

        # Create messages
        messages = [ChatMessage(role=MessageRole.USER, content=ev.prompt)]
        tool_prompt = "What's the weather in San Francisco? Also calculate 15 * 23."
        structured_prompt = "Tell me about John Smith, a 35 year old software engineer living in New York."

        # Run all models in parallel
        tasks = [
            test_single_model_all(
                name, model, ev.prompt, messages, tools, tool_prompt, structured_prompt
            )
            for name, model in models
        ]
        results_list = await asyncio.gather(*tasks)

        # Aggregate results
        all_model_results = {}
        total_result = TestResult()

        for name, model_results, result in results_list:
            all_model_results[name] = model_results
            total_result.chunks += result.chunks
            total_result.content_length += result.content_length
            total_result.tool_calls += result.tool_calls

        # Build summary
        logger.info("=" * 80)
        summary_lines = []
        for model_name in [
            "UiPathOpenAI",
            "UiPathChatBedrockConverse",
            "UiPathChatBedrock",
            "UiPathVertex",
        ]:
            if model_name in all_model_results:
                summary_lines.append(f"{model_name}:")
                results = all_model_results[model_name]
                for test_name in [
                    "complete",
                    "acomplete",
                    "stream_complete",
                    "astream_complete",
                    "chat",
                    "achat",
                    "stream_chat",
                    "astream_chat",
                    "tool_calling",
                    "structured_output",
                ]:
                    if test_name in results:
                        summary_lines.append(f"  {test_name}: {results[test_name]}")

        # Check for failures (skip "⊘ Skipped" entries - they are known limitations)
        has_failures = any(
            "✗" in str(v)
            for r in all_model_results.values()
            for v in r.values()
            if "Skipped" not in str(v)
        )

        logger.info("=" * 80)
        logger.info("TEST RESULTS")
        logger.info("=" * 80)
        logger.info(f"Success: {not has_failures}")
        logger.info("Summary:\n" + "\n".join(summary_lines))
        logger.info(f"Chunks Received: {total_result.chunks}")
        logger.info(f"Content Length: {total_result.content_length}")
        logger.info(f"Tool Calls: {total_result.tool_calls}")

        return TestOutput(
            success=not has_failures,
            result_summary="\n".join(summary_lines),
            chunks_received=total_result.chunks,
            content_length=total_result.content_length,
            tool_calls_count=total_result.tool_calls,
        )


# Create the workflow instance for UiPath runtime
agent = ChatModelTestFlow(timeout=180, verbose=True)
