from typing import List

from llama_index.core.tools import BaseTool, FunctionTool
from pydantic import BaseModel

from ..uipath_gym_types import AgentBaseClass, Datapoint


class CalculatorInput(BaseModel):
    expression: str


class CalculatorOutput(BaseModel):
    answer: float


def get_datapoints() -> List[Datapoint]:
    """Get datapoints."""
    return [
        Datapoint(
            name="datapoint_1",
            input={"expression": "15.0 + 7.0 * 3.0"},
            evaluation_criteria={
                "ExactMatchEvaluator": {"expected_output": {"answer": 36.0}},
                "ContainsEvaluator": {"search_text": "36"},
                "JsonSimilarityEvaluator": {"expected_output": {"answer": 36.0}},
                "ToolCallOrderEvaluator": {"tool_calls_order": ["multiply", "add"]},
                "ToolCallCountEvaluator": {
                    "tool_calls_count": {"multiply": (">=", 1), "add": (">=", 1)}
                },
                "ToolCallArgsEvaluator": {
                    "tool_calls": [
                        {"name": "multiply", "args": {"a": 7.0, "b": 3.0}},
                        {"name": "add", "args": {"a": 15.0, "b": 21.0}},
                    ]
                },
                "ToolCallOutputEvaluator": {
                    "tool_outputs": [
                        {"name": "multiply", "output": "21.0"},
                        {"name": "add", "output": "36.0"},
                    ]
                },
                "LLMJudgeOutputEvaluator": {"expected_output": {"answer": 36.0}},
                "LLMJudgeStrictJSONSimilarityOutputEvaluator": {
                    "expected_output": {"answer": 36.0}
                },
                "LLMJudgeTrajectoryEvaluator": {
                    "expected_agent_behavior": "The agent should have called the multiply tool with the arguments 7.0 and 3.0, and the add tool with the arguments 15.0 and 21.0."
                },
                "LLMJudgeSimulationEvaluator": {
                    "expected_agent_behavior": "The agent should have called the multiply tool with the arguments 7.0 and 3.0, and the add tool with the arguments 15.0 and 21.0."
                },
            },
            simulation_instructions="Tool multiply should return 21.0 and tool add should return 36.0.",
        ),
        Datapoint(
            name="datapoint_2",
            input={"expression": "20 + 5 * 2.0"},
            evaluation_criteria={
                "ExactMatchEvaluator": {"expected_output": {"answer": 30.0}},
                "ContainsEvaluator": {"search_text": "30"},
                "JsonSimilarityEvaluator": {"expected_output": {"answer": 30.0}},
                "ToolCallOrderEvaluator": {"tool_calls_order": ["multiply", "add"]},
                "ToolCallCountEvaluator": {
                    "tool_calls_count": {"multiply": (">=", 1), "add": (">=", 1)}
                },
                "ToolCallArgsEvaluator": {
                    "tool_calls": [
                        {"name": "multiply", "args": {"a": 5.0, "b": 2.0}},
                        {"name": "add", "args": {"a": 20.0, "b": 10.0}},
                    ]
                },
                "ToolCallOutputEvaluator": {
                    "tool_outputs": [
                        {"name": "multiply", "output": "10.0"},
                        {"name": "add", "output": "30.0"},
                    ]
                },
                "LLMJudgeOutputEvaluator": {"expected_output": {"answer": 30.0}},
                "LLMJudgeStrictJSONSimilarityOutputEvaluator": {
                    "expected_output": {"answer": 30.0}
                },
                "LLMJudgeTrajectoryEvaluator": {
                    "expected_agent_behavior": "The agent should have called the multiply tool with the arguments 5.0 and 2.0, and the add tool with the arguments 20.0 and 10.0."
                },
                "LLMJudgeSimulationEvaluator": {
                    "expected_agent_behavior": "The agent should have called the multiply tool with the arguments 5.0 and 2.0, and the add tool with the arguments 20.0 and 10.0."
                },
            },
            simulation_instructions="Tool multiply should return 10.0 and tool add should return 30.0.",
        ),
    ]


def add(a: float, b: float) -> float:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    return a + b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    return a * b


def get_tools() -> List[BaseTool]:
    """Get the calculator tools."""
    return [
        FunctionTool.from_defaults(
            fn=add,
            name="add",
            description="Add two numbers together",
        ),
        FunctionTool.from_defaults(
            fn=multiply,
            name="multiply",
            description="Multiply two numbers together",
        ),
    ]


def get_calculator_agent() -> AgentBaseClass:
    """Create and return the calculator agent configuration."""
    return AgentBaseClass(
        system_prompt="You are a calculator agent. You can perform mathematical operations using the available tools. When you have completed the calculation, provide your final result in JSON format with the key 'answer' containing the numerical result. For example: {\"answer\": 36.0}",
        user_prompt="Calculate the result of: {expression}. Provide the final answer in JSON format with the key 'answer'.",
        input_schema=CalculatorInput,
        output_schema=CalculatorOutput,
        tools=get_tools(),
        datapoints=get_datapoints(),
    )
