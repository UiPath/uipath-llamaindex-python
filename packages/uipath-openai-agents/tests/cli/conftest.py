"""Fixtures for CLI tests."""

from pathlib import Path

import pytest

# Get the tests directory path relative to this conftest file
TESTS_DIR = Path(__file__).parent.parent
MOCKS_DIR = TESTS_DIR / "mocks"


@pytest.fixture
def simple_agent_basic() -> str:
    """Load simple agent with basic configuration."""
    mock_file = MOCKS_DIR / "simple_agent_basic.py"
    with open(mock_file, "r") as file:
        data = file.read()
    return data


@pytest.fixture
def simple_agent_translation() -> str:
    """Load simple agent with translation configuration."""
    mock_file = MOCKS_DIR / "simple_agent_translation.py"
    with open(mock_file, "r") as file:
        data = file.read()
    return data


@pytest.fixture
def openai_agents_config() -> str:
    """Load openai_agents.json configuration."""
    mock_file = MOCKS_DIR / "openai_agents.json"
    with open(mock_file, "r") as file:
        data = file.read()
    return data
