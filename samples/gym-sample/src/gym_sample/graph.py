from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List

from eval.coded_evaluators import BaseEvaluator as CodedBaseEvaluator
from gym_sample.calculator.agent import get_calculator_agent
from gym_sample.calculator.evals import get_calculator_evaluators
from gym_sample.loan.agent import get_loan_agent
from gym_sample.loan.evals import get_loan_evaluators
from gym_sample.uipath_gym_types import (
    AgentBaseClass,
    BasicLoop,
    Datapoint,
)
from llama_index.core.llms import LLM
from llama_index.core.workflow import Workflow
from uipath.eval.evaluators import BaseEvaluator

from uipath_llamaindex.llms import UiPathOpenAI


def get_model() -> LLM:
    """Get the LLM (created lazily to allow environment loading)."""
    return UiPathOpenAI(model="gpt-4o-2024-11-20")


def get_agents() -> Dict[str, AgentBaseClass]:
    """Get the agents (created lazily to allow environment loading)."""
    return {
        "calculator": get_calculator_agent(),
        "loan": get_loan_agent(),
    }


def get_evaluators() -> Dict[
    str, Callable[[bool], List[BaseEvaluator | CodedBaseEvaluator]]
]:
    """Get the evaluators (created lazily to allow environment loading)."""
    return {
        "calculator": lambda include_llm_judge: get_calculator_evaluators(
            include_llm_judge
        ),
        "loan": lambda include_llm_judge: get_loan_evaluators(include_llm_judge),
    }


@asynccontextmanager
async def agents_with_datapoints(
    agent_name: str = "calculator",
) -> AsyncGenerator[List[tuple[BasicLoop, Datapoint]], None]:
    """Create and return all LlamaIndex agent loops for evaluation mode.

    Each loop pre-binds its datapoint input at build time.

    Returns:
        A list of (BasicLoop, Datapoint) tuples that can be executed.
    """
    agent_scenario = get_agents()[agent_name]

    # Create a single loop instance
    loop = BasicLoop(
        scenario=agent_scenario,
        llm=get_model(),
        print_trace=True,
        debug=False,
    )

    # Return the loop paired with each datapoint
    loops = [(loop, datapoint) for datapoint in agent_scenario.datapoints]

    yield loops


async def calculator_agent() -> Workflow:
    """Pre-configured calculator agent entry point for CLI usage.

    Example: uipath run calculator '{"expression": "2 + 2"}'

    Returns:
        Workflow configured for CLI mode (accepts runtime input).
    """
    agent_scenario = get_calculator_agent()
    loop = BasicLoop(
        scenario=agent_scenario,
        llm=get_model(),
        print_trace=True,
        debug=False,
    )
    return loop.build_cli_graph()


async def loan_agent() -> Workflow:
    """Pre-configured loan agent entry point for CLI usage.

    Returns:
        Workflow configured for CLI mode (accepts runtime input).
    """
    agent_scenario = get_loan_agent()
    loop = BasicLoop(
        scenario=agent_scenario,
        llm=get_model(),
        print_trace=True,
        debug=False,
    )
    return loop.build_cli_graph()
