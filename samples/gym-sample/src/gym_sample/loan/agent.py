from typing import List

from llama_index.core.tools import BaseTool, FunctionTool
from pydantic import BaseModel, Field

from ..tools import create_escalation_tool
from ..uipath_gym_types import AgentBaseClass, Datapoint
from .tools import (
    Google,
    LoanAgent_ApplyUiBankLoan,
    LoanAgent_ModifyLoanContract,
    LoanAgent_SendSharepointDocumentViaDocuSign,
)

SYSTEM_PROMPT = """
You are **Loan Agent**, an AI assistant tasked with automating loan creation in UiBank, modifying the loan contract and sending it to be signed via DocuSign. Your responsibilities include managing requests arrived via email. Follow these guidelines:

1. **Analyze the Email Body**:
   - Carefully read and interpret the email body to gather key information for the loan creation process.

2. **Validate Parameters Before Execution**:
   - For each function, ensure you have all the necessary parameters as per the payloadSchema.
     - If missing values are detected, initiate a task in the Action Center by calling **escalation_tool**.

3. **No Data Generation**:
   - Do **not** generate or assume missing data. All information must come from the **EmailBody** input.

4. **Dynamic Tool Selection Based on Email Input**:
   - Select the appropriate tool combination for each scenario based on the content of **EmailBody**.
    1. Apply to loan using the **LoanAgent_ApplyUiBankLoan** tool.
    2. Check the loan rate on Google using the **Google** tool.
    3. If the rate is less than the one on Google, modify the loan contract using the **LoanAgent_ModifyLoanContract** tool
    send it to be signed via DocuSign**. The location where to save the modified contract is this one: https://uipath-my.sharepoint.com/:f:/r/personal/alina_capota_uipath_com/Documents/Documents?csf=1&web=1&e=HDt89e.
    4. Send the loan contract to be signed via DocuSign using the **LoanAgent_SendSharepointDocumentViaDocuSign** tool.

5. Always escalate to a human, using escalation_tool, if:
    - There is any missing information from the request (e.g name, email address, address, loan amount, etc.)
    - There are multiple requests in the same email
    - The request is not clear
    - Input `query` as a detailed list of missing parameters.

6. **Execution Outputs**:
   - **ActionCenterTaskCreated**: Set to **True** if an Action Center task is created, otherwise set it to **False**.
   - **ActionCenterTaskURL**: Populate with the task URL if a task is created, otherwise leave blank.
   - **ExecutionDetails**: Provide a numbered step-by-step summary detailing all actions taken, including input/output values.

**Goal**:
   - Optimize and streamline loan creation operations by efficiently automating client registration with minimal user involvement while maintaining accuracy. Ensure that any escalations and additional information requirements are handled smoothly by creating Action Center tasks and resuming the workflow after tasks are completed.

When providing your final answer, return it in JSON format with the following keys:
- ExecutionDetails: A string describing what happened
- ActionCenterTaskCreated: A boolean (true/false)
- ActionCenterTaskURL: A string with the URL or null
"""


USER_PROMPT = """
The user received the following email from an loan requester:
<EmailBody> {EmailBody} </EmailBody>

Provide the final answer in JSON format.
"""


class AgentInputSchema(BaseModel):
    EmailBody: str = Field(description="The body of the request email")


class AgentOutputSchema(BaseModel):
    ExecutionDetails: str = Field(description="The execution details")
    ActionCenterTaskCreated: bool | None = Field(
        description="True if an Action Center task is created, otherwise set it to None"
    )
    ActionCenterTaskURL: str | None = Field(
        description="The URL of the Action Center task if it is created, otherwise set it to None"
    )


def get_tools() -> List[BaseTool]:
    """Get the loan agent tools."""
    return [
        FunctionTool.from_defaults(
            fn=LoanAgent_ApplyUiBankLoan,
            name="LoanAgent_ApplyUiBankLoan",
            description="Apply for a loan at UI Bank",
        ),
        FunctionTool.from_defaults(
            fn=LoanAgent_ModifyLoanContract,
            name="LoanAgent_ModifyLoanContract",
            description="Modify a loan contract",
        ),
        FunctionTool.from_defaults(
            fn=LoanAgent_SendSharepointDocumentViaDocuSign,
            name="LoanAgent_SendSharepointDocumentViaDocuSign",
            description="Send a sharepoint document via DocuSign",
        ),
        FunctionTool.from_defaults(
            fn=Google,
            name="Google",
            description="Search the web",
        ),
        create_escalation_tool(
            assign_to="alina.capota@uipath.com",
            description="Create an Action Center task when information is missing or unclear",
        ),
    ]


def get_datapoints() -> List[Datapoint]:
    """Get loan agent datapoints."""
    return [
        Datapoint(
            name="CompleteJohnLoanApplicationScenario",
            input={
                "EmailBody": "I would like to apply for a loan of $50,000 for 5 years. My email is john.doe@example.com, my name is John Doe, my address is 123 Main St, Anytown, USA, my annual income is $75,000, and I am 35 years old."
            },
            evaluation_criteria={
                "ExactMatchEvaluator": {
                    "expected_output": {"ActionCenterTaskCreated": False}
                },
                "ToolCallOrderEvaluator": {
                    "tool_calls_order": [
                        "LoanAgent_ApplyUiBankLoan",
                        "Google",
                        "LoanAgent_ModifyLoanContract",
                        "LoanAgent_SendSharepointDocumentViaDocuSign",
                    ]
                },
                "ToolCallCountEvaluator": {
                    "tool_calls_count": {
                        "LoanAgent_ApplyUiBankLoan": ("=", 1),
                        "Google": ("=", 1),
                        "LoanAgent_ModifyLoanContract": ("=", 1),
                        "LoanAgent_SendSharepointDocumentViaDocuSign": ("=", 1),
                    }
                },
                "ToolCallArgsEvaluator": {
                    "tool_calls": [
                        {
                            "name": "LoanAgent_ApplyUiBankLoan",
                            "args": {
                                "RequestorEmailAddress": "john.doe@example.com",
                                "LoanAmount": 50000,
                                "LoanTerm": 5,
                                "Income": 75000,
                                "Age": 35,
                            },
                        },
                        {
                            "name": "LoanAgent_ModifyLoanContract",
                            "args": {
                                "SharepointFolderURL": "https://uipath-my.sharepoint.com/:f:/r/personal/alina_capota_uipath_com/Documents/Documents?csf=1&web=1&e=HDt89e",
                                "InterestRate": 4,
                                "LoanAmount": 50000,
                                "BorrowerName": "John Doe",
                                "BorrowerAddress": "123 Main St, Anytown, USA",
                            },
                        },
                        {
                            "name": "LoanAgent_SendSharepointDocumentViaDocuSign",
                            "args": {
                                "SharepointFileURL": "https://uipath-my.sharepoint.com/:f:/r/personal/alina_capota_uipath_com/Documents/Documents?csf=1&web=1&e=HDt89e/New_doc.pdf",
                                "RecipientLegalName": "John Doe",
                                "RecipientEmail": "john.doe@example.com",
                            },
                        },
                    ]
                },
                "LLMJudgeOutputEvaluator": {
                    "expected_output": {
                        "ExecutionDetails": "Loan application process completed"
                    }
                },
            },
            simulation_instructions="Tool LoanAgent_ApplyUiBankLoan should return a loan application process completed",
        ),
        Datapoint(
            name="CompleteJoeLoanApplicationScenario",
            input={
                "EmailBody": "I would like to apply for a loan of $500,000 for 5 years. My email is joe.doe@example.com, my name is Joe Doe, my address is 123 Main St, Anytown, USA, my annual income is $735,000, and I am 55 years old."
            },
            evaluation_criteria={
                "ExactMatchEvaluator": {
                    "expected_output": {"ActionCenterTaskCreated": False}
                },
                "ToolCallOrderEvaluator": {
                    "tool_calls_order": [
                        "LoanAgent_ApplyUiBankLoan",
                        "Google",
                        "LoanAgent_ModifyLoanContract",
                        "LoanAgent_SendSharepointDocumentViaDocuSign",
                    ]
                },
                "ToolCallCountEvaluator": {
                    "tool_calls_count": {
                        "LoanAgent_ApplyUiBankLoan": ("=", 1),
                        "Google": ("=", 1),
                        "LoanAgent_ModifyLoanContract": ("=", 1),
                        "LoanAgent_SendSharepointDocumentViaDocuSign": ("=", 1),
                    }
                },
                "ToolCallArgsEvaluator": {
                    "tool_calls": [
                        {
                            "name": "LoanAgent_ApplyUiBankLoan",
                            "args": {
                                "RequestorEmailAddress": "joe.doe@example.com",
                                "LoanAmount": 500000,
                                "LoanTerm": 5,
                                "Income": 735000,
                                "Age": 55,
                            },
                        },
                        {
                            "name": "LoanAgent_ModifyLoanContract",
                            "args": {
                                "SharepointFolderURL": "https://uipath-my.sharepoint.com/:f:/r/personal/alina_capota_uipath_com/Documents/Documents?csf=1&web=1&e=HDt89e",
                                "InterestRate": 4,
                                "LoanAmount": 500000,
                                "BorrowerName": "Joe Doe",
                                "BorrowerAddress": "123 Main St, Anytown, USA",
                            },
                        },
                        {
                            "name": "LoanAgent_SendSharepointDocumentViaDocuSign",
                            "args": {
                                "SharepointFileURL": "https://uipath-my.sharepoint.com/:f:/r/personal/alina_capota_uipath_com/Documents/Documents?csf=1&web=1&e=HDt89e/New_doc.pdf",
                                "RecipientLegalName": "Joe Doe",
                                "RecipientEmail": "joe.doe@example.com",
                            },
                        },
                    ]
                },
                "LLMJudgeOutputEvaluator": {
                    "expected_output": {
                        "ExecutionDetails": "Loan application process completed"
                    }
                },
            },
            simulation_instructions="Tool LoanAgent_ApplyUiBankLoan should return a loan application process completed",
        ),
    ]


def get_loan_agent() -> AgentBaseClass:
    """Create and return the loan agent configuration."""
    return AgentBaseClass(
        input_schema=AgentInputSchema,
        output_schema=AgentOutputSchema,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=USER_PROMPT,
        tools=get_tools(),
        datapoints=get_datapoints(),
    )
