from typing import List

from eval.coded_evaluators import (
    BaseEvaluator as CodedBaseEvaluator,
)
from eval.coded_evaluators import (
    ExactMatchEvaluator as CodedExactMatchEvaluator,
)
from eval.coded_evaluators import (
    LLMJudgeOutputEvaluator as CodedLLMJudgeOutputEvaluator,
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
from uipath.eval.evaluators import BaseEvaluator


def get_loan_evaluators(
    include_llm_judge: bool = False,
) -> List[BaseEvaluator | CodedBaseEvaluator]:
    """Create evaluators using the new CodedEvaluator approach."""
    evaluators: List[BaseEvaluator | CodedBaseEvaluator] = [
        CodedExactMatchEvaluator.model_validate(
            {
                "config": {
                    "negated": False,
                    "target_output_key": "ActionCenterTaskCreated",
                }
            }
        ),
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
    ]

    if include_llm_judge:
        evaluators.extend(
            [
                CodedLLMJudgeOutputEvaluator.model_validate(
                    {
                        "config": {
                            "target_output_key": "ExecutionDetails",
                            "model": "gpt-4o-2024-11-20",
                            "temperature": 0.0,
                        },
                    }
                ),
            ]
        )

    return evaluators
