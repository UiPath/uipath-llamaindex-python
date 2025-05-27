import json
import os
import sys
import io  # Added
from unittest.mock import patch  # Added

import pytest

# Need these for type hints in mocks and for constructing mock return values
from llama_index.core.workflow import HumanResponseEvent, Context  # Added

# The function we are testing
from uipath_llamaindex._cli.cli_run import llamaindex_run_middleware  # Added


# Determine the root directory of the project (uipath-llamaindex-python)
# Assumes this test file is at tests/cli/test_run_simple_hitl_agent.py
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AGENT_DIR = os.path.join(ROOT_DIR, "samples", "simple-hitl-agent")


def run_agent_test(human_response: str, expected_outcome: str):
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

    # Patch sys.stdout to capture print outputs.
    # Patch Context.wait_for_event with our dynamic async mock.
    with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, patch('llama_index.core.workflow.Context.wait_for_event', new=dynamic_wait_for_event_mock):

        middleware_result = llamaindex_run_middleware(
            entrypoint="agent",  # Workflow name from llama_index.json
            input=json.dumps({"hack": {}}),  # Input for the agent, as per uipath.json
            resume=False
        )

    # Restore current working directory
    os.chdir(original_cwd)

    # --- Assertions ---
    assert middleware_result.error_message is None, f"Middleware failed: {middleware_result.error_message}\\nStdout: {mock_stdout.getvalue()}"

    full_stdout = mock_stdout.getvalue()

    # 0. Check for initial agent message
    assert "Researching company..." in full_stdout, \
        f"'Researching company...' not found in stdout.\\nStdout: {full_stdout}"

    # 1. Check for the HITL prompt (from InputRequiredEvent printed by runtime)
    assert "InputRequiredEvent" in full_stdout, f"InputRequiredEvent not found in stdout.\\nStdout: {full_stdout}"
    assert "Are you sure you want to proceed?" in full_stdout, f"HITL prompt 'Are you sure you want to proceed?' not found in stdout.\\nStdout: {full_stdout}"

    # 2. Check for the "Received response" message (from agent's print statement)
    assert f"Received response: {human_response}" in full_stdout, f"'Received response: {human_response}' not found in stdout.\\nStdout: {full_stdout}"

    # 3. Check for the expected outcome (from StopEvent printed by runtime)
    assert "StopEvent" in full_stdout, f"StopEvent not found in stdout.\\nStdout: {full_stdout}"
    # The expected_outcome is the 'result' field of the StopEvent.
    # Example StopEvent string: StopEvent(result='Research completed successfully.')
    assert f"result='{expected_outcome}'" in full_stdout, f"Expected outcome '{expected_outcome}' not found in StopEvent in stdout.\\nStdout: {full_stdout}"


def test_run_simple_hitl_agent_yes_response():
    """Tests the simple-hitl-agent with a 'yes' response to the prompt."""
    run_agent_test(human_response="yes", expected_outcome="Research completed successfully.")

def test_run_simple_hitl_agent_no_response():
    """Tests the simple-hitl-agent with a 'no' response to the prompt."""
    run_agent_test(human_response="no", expected_outcome="Research task aborted.")

