from typing import Any, Dict

from llama_index.core.tools import FunctionTool
from pydantic import BaseModel, Field

META_DESCRIPTION_ESCALATION_TOOL: str = """This is an escalation. This tool must be called separately from other tool calls (i.e. not in parallel with other tool calls).
This is because you must wait for the response before deciding what tool to call next.
"""


class RaiseErrorInput(BaseModel):
    message: str = Field(
        description="The error message to display to the user. This should be a brief on line message."
    )
    details: str | None = Field(
        default=None,
        description="Optional additional details about the error. This can be a multiline text with more details. Only populate this if there are relevant details not already captured in the error message.",
    )


class StateBaseClass(BaseModel):
    class Config:
        extra = "allow"  # Allow extra fields from input_schema

    messages: list[Dict[str, Any]] = []
    result: Dict[str, Any] = {}
    raised_error: RaiseErrorInput | None = None
    run_init_state: Dict[str, str] = {}


class EndExecutionDefaultOutput(BaseModel):
    result: Dict[str, Any] = {}


def create_escalation_tool(
    assign_to: str, description: str = "", return_message: str | None = None
) -> FunctionTool:
    """Create an escalation tool for agent scenarios.

    Args:
        assign_to: The person/team to assign the escalated query to
        description: Additional description for the tool
        return_message: Optional custom return message

    Returns:
        FunctionTool configured as an escalation tool
    """

    def escalation_tool(query: str) -> str:
        """Escalate the query to another team or person.

        Args:
            query: The query string to escalate
        """
        if return_message:
            return return_message
        return f'The escalation was successful. A task has been created for this query: "{query}", and assigned to {assign_to}.'

    tool_description = (
        f"{META_DESCRIPTION_ESCALATION_TOOL}{description}"
        if description
        else META_DESCRIPTION_ESCALATION_TOOL
    )

    return FunctionTool.from_defaults(
        fn=escalation_tool,
        name="escalation_tool",
        description=tool_description,
    )
