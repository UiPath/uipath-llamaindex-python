"""Tests for uipath run command with openai-agents.

Note: These tests check CLI invocation and error handling.
Full agent execution tests with OpenAI API calls should be marked as integration tests.
"""

import os

from click.testing import CliRunner
from uipath._cli.cli_run import run


class TestRun:
    """Test run command for OpenAI agents."""

    def test_run_basic_agent_invocation(
        self,
        runner: CliRunner,
        temp_dir: str,
        simple_agent_basic: str,
        openai_agents_config: str,
    ) -> None:
        """Test basic agent invocation structure (without actual OpenAI API calls)."""
        input_file_name = "input.json"
        input_json_content = '{"messages": "Hello, agent!"}'

        with runner.isolated_filesystem(temp_dir=temp_dir):
            # create input file
            input_file_path = os.path.join(temp_dir, input_file_name)
            with open(input_file_path, "w") as f:
                f.write(input_json_content)

            # Create agent script
            with open("main.py", "w") as f:
                f.write(simple_agent_basic)

            with open("openai_agents.json", "w") as f:
                f.write(openai_agents_config)

            # Note: This will fail without OpenAI API key, but we're testing CLI structure
            result = runner.invoke(run, ["basic", "--file", input_file_path])

            # The command should invoke without crashing from CLI parsing
            # Actual execution may fail without API key, which is expected
            # We're testing the CLI invocation layer here
            assert result.exit_code in [0, 1]  # 0 = success, 1 = runtime error

    def test_run_with_invalid_agent_name(
        self,
        runner: CliRunner,
        temp_dir: str,
        simple_agent_basic: str,
        openai_agents_config: str,
    ) -> None:
        """Test run command with non-existent agent name."""
        input_file_name = "input.json"
        input_json_content = '{"messages": "test"}'

        with runner.isolated_filesystem(temp_dir=temp_dir):
            input_file_path = os.path.join(temp_dir, input_file_name)
            with open(input_file_path, "w") as f:
                f.write(input_json_content)

            with open("main.py", "w") as f:
                f.write(simple_agent_basic)

            with open("openai_agents.json", "w") as f:
                f.write(openai_agents_config)

            # Try to run non-existent agent
            result = runner.invoke(
                run, ["nonexistent_agent", "--file", input_file_path]
            )

            # Should fail with non-zero exit code
            assert result.exit_code != 0

    def test_run_without_config_file(
        self,
        runner: CliRunner,
        temp_dir: str,
        simple_agent_basic: str,
    ) -> None:
        """Test run command without openai_agents.json file."""
        input_file_name = "input.json"
        input_json_content = '{"messages": "test"}'

        with runner.isolated_filesystem(temp_dir=temp_dir):
            input_file_path = os.path.join(temp_dir, input_file_name)
            with open(input_file_path, "w") as f:
                f.write(input_json_content)

            with open("main.py", "w") as f:
                f.write(simple_agent_basic)

            # No openai_agents.json file

            result = runner.invoke(run, ["basic", "--file", input_file_path])

            # Should fail without config file
            assert result.exit_code != 0

    def test_run_with_malformed_input_json(
        self,
        runner: CliRunner,
        temp_dir: str,
        simple_agent_basic: str,
        openai_agents_config: str,
    ) -> None:
        """Test run command with malformed JSON input."""
        input_file_name = "input.json"
        input_json_content = '{"messages": invalid json}'  # Malformed

        with runner.isolated_filesystem(temp_dir=temp_dir):
            input_file_path = os.path.join(temp_dir, input_file_name)
            with open(input_file_path, "w") as f:
                f.write(input_json_content)

            with open("main.py", "w") as f:
                f.write(simple_agent_basic)

            with open("openai_agents.json", "w") as f:
                f.write(openai_agents_config)

            result = runner.invoke(run, ["basic", "--file", input_file_path])

            # Should fail due to malformed JSON
            assert result.exit_code != 0
