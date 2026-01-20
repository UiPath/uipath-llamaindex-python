import os
import tempfile
from typing import Generator

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click CLI test runner with in-memory database for tests."""
    # Use in-memory SQLite database to avoid Windows file locking issues
    return CliRunner(env={"UIPATH_STATE_FILE_PATH": ":memory:"})


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Set environment variable to use in-memory database
        old_value = os.environ.get("UIPATH_STATE_FILE_PATH")
        os.environ["UIPATH_STATE_FILE_PATH"] = ":memory:"
        try:
            yield tmp_dir
        finally:
            # Restore original value
            if old_value is None:
                os.environ.pop("UIPATH_STATE_FILE_PATH", None)
            else:
                os.environ["UIPATH_STATE_FILE_PATH"] = old_value
