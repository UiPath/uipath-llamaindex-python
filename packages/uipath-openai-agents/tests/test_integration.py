"""Integration test demonstrating new runtime features."""

import sys
from pathlib import Path

import pytest

# Add samples directory to path
samples_dir = Path(__file__).parent.parent / "samples" / "agent-as-tools"
sys.path.insert(0, str(samples_dir))

from main import (  # type: ignore  # noqa: E402
    TranslationInput,
    TranslationOutput,
    orchestrator_agent,
)

from uipath_openai_agents.runtime.errors import (  # noqa: E402
    UiPathOpenAIAgentsErrorCode,
    UiPathOpenAIAgentsRuntimeError,
)
from uipath_openai_agents.runtime.runtime import (  # noqa: E402
    UiPathOpenAIAgentRuntime,
)
from uipath_openai_agents.runtime.schema import (  # noqa: E402
    get_entrypoints_schema,
)
from uipath_openai_agents.runtime.storage import (  # noqa: E402
    SqliteAgentStorage,
)


def test_error_handling():
    """Test that error handling works correctly."""
    error = UiPathOpenAIAgentsRuntimeError(
        code=UiPathOpenAIAgentsErrorCode.AGENT_EXECUTION_FAILURE,
        title="Test error",
        detail="This is a test error",
    )

    # Verify error can be created and contains the detail message
    assert isinstance(error, UiPathOpenAIAgentsRuntimeError)
    assert "This is a test error" in str(error)

    # Verify error can be raised
    with pytest.raises(UiPathOpenAIAgentsRuntimeError) as exc_info:
        raise error

    assert "This is a test error" in str(exc_info.value)


def test_schema_extraction_with_new_serialization():
    """Test that schema extraction works with the serialization improvements."""
    schema = get_entrypoints_schema(orchestrator_agent)

    # Verify input schema (messages format)
    assert "input" in schema
    assert "message" in schema["input"]["properties"]

    # Verify output schema (from agent's output_type)
    assert "output" in schema
    assert "original_text" in schema["output"]["properties"]
    assert "translations" in schema["output"]["properties"]
    assert "languages_used" in schema["output"]["properties"]

    # Verify title from output_type
    assert schema["output"]["title"] == "TranslationOutput"


async def test_runtime_initialization_with_storage():
    """Test that runtime can be initialized with storage."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test.db"

        # Create storage
        storage = SqliteAgentStorage(storage_path)
        await storage.setup()

        # Create runtime with storage
        runtime = UiPathOpenAIAgentRuntime(
            agent=orchestrator_agent,
            runtime_id="test_runtime",
            entrypoint="test",
            storage_path=storage_path,
            storage=storage,
        )

        # Verify runtime initialized correctly
        assert runtime.storage is not None
        assert runtime.runtime_id == "test_runtime"

        # Test schema generation
        schema = await runtime.get_schema()
        assert schema.type == "agent"
        assert "message" in schema.input["properties"]
        assert "original_text" in schema.output["properties"]

        await storage.dispose()


async def test_storage_operations():
    """Test storage save/load operations."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test_storage.db"

        storage = SqliteAgentStorage(storage_path)
        await storage.setup()

        # Test state save/load
        runtime_id = "test_runtime_123"
        test_state = {"step": "translation", "progress": 50}

        await storage.save_state(runtime_id, test_state)
        loaded_state = await storage.load_state(runtime_id)

        assert loaded_state == test_state

        # Test key-value operations
        await storage.set_value(runtime_id, "test_namespace", "key1", "value1")
        value = await storage.get_value(runtime_id, "test_namespace", "key1")

        assert value == "value1"

        # Test dict value
        await storage.set_value(
            runtime_id, "test_namespace", "dict_key", {"nested": "value"}
        )
        dict_value = await storage.get_value(runtime_id, "test_namespace", "dict_key")

        assert dict_value == {"nested": "value"}

        await storage.dispose()


def test_pydantic_models():
    """Test that Pydantic models work correctly with serialization."""
    # Create input model
    input_data = TranslationInput(
        text="Hello, world!", target_languages=["Spanish", "French"]
    )

    assert input_data.text == "Hello, world!"
    assert len(input_data.target_languages) == 2

    # Create output model
    output_data = TranslationOutput(
        original_text="Hello, world!",
        translations={"Spanish": "¡Hola, mundo!", "French": "Bonjour, monde!"},
        languages_used=["Spanish", "French"],
    )

    assert output_data.original_text == "Hello, world!"
    assert len(output_data.translations) == 2
    assert output_data.translations["Spanish"] == "¡Hola, mundo!"

    # Test model_dump for serialization
    serialized = output_data.model_dump()
    assert isinstance(serialized, dict)
    assert serialized["original_text"] == "Hello, world!"
