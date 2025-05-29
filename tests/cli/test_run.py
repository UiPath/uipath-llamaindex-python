import os

import pytest
from click.testing import CliRunner
from uipath._cli.cli_run import run  # type: ignore


@pytest.fixture
def mock_env_vars():
    return {
        "UIPATH_CONFIG_PATH": "test_config.json",
        "UIPATH_JOB_KEY": "test-job-id",
        "UIPATH_TRACE_ID": "test-trace-id",
        "UIPATH_TRACING_ENABLED": "true",
        "UIPATH_PARENT_SPAN_ID": "test-parent-span",
        "UIPATH_ROOT_SPAN_ID": "test-root-span",
        "UIPATH_ORGANIZATION_ID": "test-org-id",
        "UIPATH_TENANT_ID": "test-tenant-id",
        "UIPATH_PROCESS_UUID": "test-process-id",
        "UIPATH_FOLDER_KEY": "test-folder-key",
        "LOG_LEVEL": "DEBUG",
    }


class TestRun:
    def test_run_return_dict_from_str(
        self,
        runner: CliRunner,
        temp_dir: str,
        simple_script_basic_config: str,
        llama_config: str,
    ) -> None:
        """Test configuration file generation with StartEvent and StopEvent."""
        input_file_name = "input.json"
        mock_topic = "mock topic"
        input_json_content = f'{{"topic": "{mock_topic}"}}'
        with runner.isolated_filesystem(temp_dir=temp_dir):
            # create input file
            input_file_path = os.path.join(temp_dir, input_file_name)
            with open(input_file_path, "w") as f:
                f.write(input_json_content)
            # Create agent script
            with open("main.py", "w") as f:
                f.write(simple_script_basic_config)

            with open("llama_index.json", "w") as f:
                f.write(llama_config)

            result = runner.invoke(run, ["agent", "--file", input_file_path])
            assert result.exit_code == 0
            joke = f"response for prompt: Write your best joke about {mock_topic}."
            expected_result = f"{{'result': 'Mock critique for: {joke}'}}"
            assert expected_result in result.output
            assert "Successful execution." in result.output

    def test_run_success(
        self,
        runner: CliRunner,
        temp_dir: str,
        simple_script_custom_config: str,
        llama_config: str,
    ) -> None:
        """Test configuration file generation with StartEvent and StopEvent."""
        input_file_name = "input.json"
        mock_topic = "mock topic"
        input_json_content = f'{{"topic": "{mock_topic}"}}'

        with runner.isolated_filesystem(temp_dir=temp_dir):
            # create input file
            input_file_path = os.path.join(temp_dir, input_file_name)
            with open(input_file_path, "w") as f:
                f.write(input_json_content)
            # Create agent script
            with open("main.py", "w") as f:
                f.write(simple_script_custom_config)

            with open("llama_index.json", "w") as f:
                f.write(llama_config)

            result = runner.invoke(run, ["agent", "--file", input_file_path])
            assert result.exit_code == 0
            joke = f"response for prompt: Write your best joke about {mock_topic}."
            expected_result = f"{{'joke': '{joke}', 'critique': 'Mock critique for: {joke}', 'param': None}}"
            assert expected_result in result.output
            assert "Successful execution." in result.output
