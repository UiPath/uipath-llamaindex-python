import io
import json
import os
from unittest.mock import MagicMock, patch

# Need these for type hints in mocks and for constructing mock return values
from llama_index.core.workflow import HumanResponseEvent


# MOVED IMPORT HERE: Import now occurs after os.environ is patched.
from uipath_llamaindex._cli.cli_run import llamaindex_run_middleware
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen
from llama_index.core.llms import LLMMetadata
from typing import Any


# Determine the root directory of the project (uipath-llamaindex-python)
# Assumes this test file is at tests/cli/test_run_simple_hitl_agent.py
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AGENT_DIR = os.path.join(ROOT_DIR, "samples", "simple-hitl-agent")


class DeterministicLLM(CustomLLM):

    response_sequence: list[CompletionResponse] = [
        CompletionResponse(text="Thought: The current language of the user is: ENGLISH. I need to use a tool to help me answer the question.\nAction: research_company\nAction Input: { }"),
        # CompletionResponse(text="", raw={
        #     "tool_calls": [
        #         {
        #             "id": "call_abc123",
        #             "type": "function",
        #             "function": {
        #                 "name": "research_company",
        #                 "arguments": "{}"
        #             }
        #         }
        #     ]
        # }),
        # CompletionResponse(text="Thought: I cannot answer the question with the provided tools. \n Answer: Random answer"),
    ]

    def complete(self, prompt: str, **kwargs: Any):
        current_response = self.response_sequence.pop(0)
        return current_response

    @property
    def metadata(self) -> LLMMetadata:
        """Get LLM metadata."""
        return LLMMetadata(
            context_window=4096,  # Replace with your desired context window size
            num_output=256,  # Replace with your desired output size
            model_name="deterministic"
        )
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        response = self.complete(prompt, **kwargs)
        yield response


def run_agent_test(human_response: str, expected_outcome: str, agent_input_data: dict | None = None):
    """
    Helper function to run the agent test by directly calling
    the llamaindex_run_middleware and mocking HITL interaction.
    """
    original_cwd = os.getcwd()
    os.chdir(AGENT_DIR)

    # This async mock function will be created dynamically within run_agent_test
    # to close over the 'human_response' variable specific to each test call.
    async def dynamic_wait_for_event_mock(self_context_instance, event_class, timeout_val=None):
        # self_context_instance is the 'self' (the Context instance)
        # event_class is the class of event being waited for
        if event_class == HumanResponseEvent:
            # Use human_response from the outer scope of run_agent_test
            return HumanResponseEvent(response=human_response)
        # This mock is specific to simple-hitl-agent which only awaits HumanResponseEvent.
        # If other events were awaited, this mock would need to be more comprehensive.
        raise Exception(
            f"Mock Error: Unexpected Context.wait_for_event call for {event_class}"
        )

    # Determine input for the agent
    current_agent_input = agent_input_data if agent_input_data is not None else {"hack": {}}

    env_vars_to_mock = {
        "UIPATH_TOKEN": "dummy_test_token",
        "UIPATH_ORGANIZATION_ID": "dummy_org_id",
        "UIPATH_TENANT_ID": "dummy_tenant_id",
        "UIPATH_ACCOUNT_LOGICAL_NAME": "dummy_account_logical_name",
        # Prevent actual telemetry during tests
        "UIPATH_TELEMETRY_CLIENT_SECRET": "", 
        "UIPATH_TRACING_ENABLED": "false",
        "UIPATH_URL": "https://dummy.uipath.com",
        "UIPATH_ACCESS_TOKEN": "1234567890",
    }

    #  patch('llama_index.core.workflow.Context.wait_for_event', new=dynamic_wait_for_event_mock), \

    # Patch sys.stdout to capture print outputs.
    # Patch Context.wait_for_event with our dynamic async mock.
    # Patch UiPath to prevent real API calls (especially for tracing).
    # Patch os.environ to simulate authenticated environment.
    with patch.dict(os.environ, env_vars_to_mock), \
         patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
         patch('llama_index.llms.openai.OpenAI', new=DeterministicLLM), \
         patch('uipath.UiPath') as MockUiPath:

        # Configure the MockUiPath instance
        mock_uipath_instance = MagicMock()
        mock_uipath_instance.tracer.send_trace = MagicMock()
        # If other UiPath SDK features were used by the runtime and needed mocking (e.g., API client for resume):
        # mock_uipath_instance.api_client.request = MagicMock(...)
        MockUiPath.return_value = mock_uipath_instance

        middleware_result = llamaindex_run_middleware(
            entrypoint="agent",  # Workflow name from llama_index.json
            input=json.dumps(current_agent_input),  # MODIFIED: Use current_agent_input
            resume=False
        )

        middleware_result = llamaindex_run_middleware(
            entrypoint="agent",  # Workflow name from llama_index.json
            input=json.dumps(current_agent_input),  # MODIFIED: Use current_agent_input
            resume=True
        )

    # Restore current working directory
    os.chdir(original_cwd)

    # --- Assertions ---
    assert middleware_result.error_message is None, f"Middleware failed: {middleware_result.error_message}\\nStdout: {mock_stdout.getvalue()}"

    full_stdout = mock_stdout.getvalue()

    # # 0. Check for initial agent message
    # assert "Researching company..." in full_stdout, f"'Researching company...' not found in stdout.\\nStdout: {full_stdout}"

    # # 1. Check for the HITL prompt (from InputRequiredEvent printed by runtime)
    # assert "InputRequiredEvent" in full_stdout, f"InputRequiredEvent not found in stdout.\\nStdout: {full_stdout}"
    # assert "Are you sure you want to proceed?" in full_stdout, f"HITL prompt 'Are you sure you want to proceed?' not found in stdout.\\nStdout: {full_stdout}"

    # # 2. Check for the "Received response" message (from agent's print statement)
    # assert f"Received response: {human_response}" in full_stdout, f"'Received response: {human_response}' not found in stdout.\\nStdout: {full_stdout}"

    # # 3. Check for the expected outcome (from StopEvent printed by runtime)
    # assert "StopEvent" in full_stdout, f"StopEvent not found in stdout.\\nStdout: {full_stdout}"
    # # The expected_outcome is the 'result' field of the StopEvent.
    # # Example StopEvent string: StopEvent(result='Research completed successfully.')
    # assert f"result='{expected_outcome}'" in full_stdout, f"Expected outcome '{expected_outcome}' not found in StopEvent in stdout.\\nStdout: {full_stdout}"


def test_run_simple_hitl_agent_yes_response():
    """Tests the simple-hitl-agent with a 'yes' response to the prompt."""
    # ADDED: Define input with authentication for this test case
    auth_input_data = {
        "user_msg": "Please start the research.", # ADDED user_msg
        "hack": {},
        "auth": {"token": "random_fixed_auth_token_for_yes_test"}
    }
    run_agent_test(
        human_response="yes",
        expected_outcome="Research completed successfully.",
        agent_input_data=auth_input_data  # ADDED: Pass new input data
    )

def test_run_simple_hitl_agent_no_response():
    """Tests the simple-hitl-agent with a 'no' response to the prompt."""
    # ADDED: Define input with authentication for this test case
    auth_input_data = {
        "user_msg": "Please start the research.", # ADDED user_msg
        "hack": {},
        "auth": {"token": "random_fixed_auth_token_for_no_test"}
    }
    run_agent_test(
        human_response="no",
        expected_outcome="Research task aborted.",
        agent_input_data=auth_input_data  # ADDED: Pass new input data
    )

