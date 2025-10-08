from typing import List

from eval.coded_evaluators import (
    BaseEvaluator as CodedBaseEvaluator,
)
from eval.coded_evaluators import (
    ContainsEvaluator as CodedContainsEvaluator,
)
from eval.coded_evaluators import (
    ExactMatchEvaluator as CodedExactMatchEvaluator,
)
from eval.coded_evaluators import (
    JsonSimilarityEvaluator as CodedJsonSimilarityEvaluator,
)
from eval.coded_evaluators import (
    LLMJudgeOutputEvaluator as CodedLLMJudgeOutputEvaluator,
)
from eval.coded_evaluators import (
    LLMJudgeSimulationTrajectoryEvaluator as CodedLLMJudgeSimulationTrajectoryEvaluator,
)
from eval.coded_evaluators import (
    LLMJudgeStrictJSONSimilarityOutputEvaluator as CodedLLMJudgeStrictJSONSimilarityOutputEvaluator,
)
from eval.coded_evaluators import (
    LLMJudgeTrajectoryEvaluator as CodedLLMJudgeTrajectoryEvaluator,
)
from eval.coded_evaluators import (
    ToolCallArgsEvaluator as CodedToolCallArgsEvaluator,
)
from eval.coded_evaluators import (
    ToolCallCountEvaluator as CodedToolCallCountEvaluator,
)
from eval.coded_evaluators import (
    ToolCallOrderEvaluator as CodedToolCallOrderEvaluator,
)
from eval.coded_evaluators import (
    ToolCallOutputEvaluator as CodedToolCallOutputEvaluator,
)
from uipath.eval.evaluators import BaseEvaluator


def get_calculator_evaluators(
    include_llm_judge: bool = False,
) -> List[BaseEvaluator | CodedBaseEvaluator]:
    """Create evaluators using the new CodedEvaluator approach."""
    evaluators: List[BaseEvaluator | CodedBaseEvaluator] = [
        CodedExactMatchEvaluator.model_validate({"config": {"negated": False}}),
        CodedContainsEvaluator.model_validate({"config": {"negated": False}}),
        CodedJsonSimilarityEvaluator.model_validate({"config": {}}),
        CodedToolCallOrderEvaluator.model_validate(
            {
                "config": {
                    "strict": False,
                },
            }
        ),
        CodedToolCallCountEvaluator.model_validate(
            {
                "config": {
                    "strict": False,
                },
            }
        ),
        CodedToolCallArgsEvaluator.model_validate(
            {
                "config": {
                    "strict": False,
                    "subset": False,
                },
            }
        ),
        CodedToolCallOutputEvaluator.model_validate(
            {
                "config": {
                    "strict": False,
                },
            }
        ),
    ]

    if include_llm_judge:
        evaluators.extend(
            [
                CodedLLMJudgeOutputEvaluator.model_validate(
                    {
                        "config": {
                            "model": "gpt-4o-2024-11-20",
                            "temperature": 0.0,
                        },
                    }
                ),
                CodedLLMJudgeStrictJSONSimilarityOutputEvaluator.model_validate(
                    {
                        "config": {
                            "model": "gpt-4o-2024-11-20",
                            "temperature": 0.0,
                        },
                    }
                ),
                CodedLLMJudgeTrajectoryEvaluator.model_validate(
                    {
                        "config": {
                            "model": "gpt-4o-2024-11-20",
                            "temperature": 0.0,
                        },
                    }
                ),
                CodedLLMJudgeSimulationTrajectoryEvaluator.model_validate(
                    {
                        "config": {
                            "model": "gpt-4o-2024-11-20",
                            "temperature": 0.0,
                        },
                    }
                ),
            ]
        )

    return evaluators
