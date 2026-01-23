"""Integration test demonstrating new runtime features."""

import os
import sys
from pathlib import Path

import pytest

# Set up mock environment variables for sample imports
os.environ.setdefault("UIPATH_URL", "https://mock.uipath.com")
os.environ.setdefault("UIPATH_ORGANIZATION_ID", "mock-org-id")
os.environ.setdefault("UIPATH_TENANT_ID", "mock-tenant-id")
os.environ.setdefault("UIPATH_ACCESS_TOKEN", "mock-token")

# Add samples directory to path
samples_dir = Path(__file__).parent.parent / "samples" / "agent-as-tools"
sys.path.insert(0, str(samples_dir))

from main import (  # type: ignore  # noqa: E402
    TranslationOutput,
    main,
)

from uipath_openai_agents.runtime.errors import (  # noqa: E402
    UiPathOpenAIAgentsErrorCode,
    UiPathOpenAIAgentsRuntimeError,
)
from uipath_openai_agents.runtime.schema import (  # noqa: E402
    get_entrypoints_schema,
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
    orchestrator_agent = main()
    schema = get_entrypoints_schema(orchestrator_agent)

    # Verify input schema (messages format)
    assert "input" in schema
    assert "messages" in schema["input"]["properties"]

    # Verify output schema (from agent's output_type)
    assert "output" in schema
    assert "original_text" in schema["output"]["properties"]
    assert "translations" in schema["output"]["properties"]
    assert "languages_used" in schema["output"]["properties"]

    # Verify title from output_type
    assert schema["output"]["title"] == "TranslationOutput"


def test_pydantic_models():
    """Test that Pydantic models work correctly with serialization."""
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
