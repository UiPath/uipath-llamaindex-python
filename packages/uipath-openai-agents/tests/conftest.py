import tempfile
from typing import Generator
from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def use_in_memory_database():
    """Patch storage to use in-memory SQLite database for all tests.

    This prevents Windows file locking issues during test cleanup.
    """
    with patch(
        "uipath_openai_agents.runtime.factory.UiPathOpenAIAgentRuntimeFactory._get_storage_path",
        return_value=":memory:",
    ):
        yield


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir
