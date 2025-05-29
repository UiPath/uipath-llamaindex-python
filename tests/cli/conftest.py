import os

import pytest


@pytest.fixture
def simple_script_basic_config() -> str:
    if os.path.isfile("../mocks/simple_script_basic_config.py"):
        with open("../mocks/simple_script_basic_config.py", "r") as file:
            data = file.read()
    else:
        with open("tests/mocks/simple_script_basic_config.py", "r") as file:
            data = file.read()
    return data


@pytest.fixture
def simple_script_custom_config() -> str:
    if os.path.isfile("../mocks/simple_script_custom_config.py"):
        with open("../mocks/simple_script_custom_config.py", "r") as file:
            data = file.read()
    else:
        with open("tests/mocks/simple_script_custom_config.py", "r") as file:
            data = file.read()
    return data


@pytest.fixture
def llama_config() -> str:
    if os.path.isfile("../mocks/llama_index.json"):
        with open("../mocks/llama_index.json", "r") as file:
            data = file.read()
    else:
        with open("tests/mocks/llama_index.json", "r") as file:
            data = file.read()
    return data
