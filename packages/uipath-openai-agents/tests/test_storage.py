"""Tests for SqliteAgentStorage class."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from uipath.runtime import (
    UiPathApiTrigger,
    UiPathResumeTrigger,
    UiPathResumeTriggerName,
    UiPathResumeTriggerType,
)

from uipath_openai_agents.runtime.storage import SqliteAgentStorage


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    name: str
    value: int


class TestSqliteAgentStorageInitialization:
    """Test storage initialization and setup."""

    @pytest.mark.asyncio
    async def test_setup_creates_database_file(self, tmp_path: Path):
        """Test that setup creates the database file."""
        db_path = tmp_path / "test.db"
        async with SqliteAgentStorage(str(db_path)) as storage:
            await storage.setup()
            assert db_path.exists()

    @pytest.mark.asyncio
    async def test_setup_creates_directory_if_missing(self, tmp_path: Path):
        """Test that setup creates parent directories if they don't exist."""
        db_path = tmp_path / "subdir" / "another" / "test.db"
        async with SqliteAgentStorage(str(db_path)) as storage:
            await storage.setup()
            assert db_path.exists()
            assert db_path.parent.exists()

    @pytest.mark.asyncio
    async def test_setup_is_idempotent(self, tmp_path: Path):
        """Test that setup can be called multiple times safely."""
        db_path = tmp_path / "test.db"
        async with SqliteAgentStorage(str(db_path)) as storage:
            await storage.setup()
            await storage.setup()  # Should not raise
            assert db_path.exists()


class TestTriggerOperations:
    """Test resume trigger save and retrieval operations."""

    @pytest.fixture
    async def storage(self):
        """Create a SqliteAgentStorage instance with temporary database file."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        try:
            async with SqliteAgentStorage(str(temp_db.name)) as storage:
                await storage.setup()
                yield storage
        finally:
            if os.path.exists(temp_db.name):
                os.remove(temp_db.name)

    @pytest.mark.asyncio
    async def test_save_trigger_basic(self, storage: SqliteAgentStorage):
        """Test saving a basic resume trigger."""
        trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="queue-123",
            folder_path="/test/folder",
            folder_key="folder-456",
            payload={"data": "test"},
            interrupt_id="interrupt-789",
        )

        await storage.save_triggers("runtime-1", [trigger])

        # Verify it was saved
        triggers = await storage.get_triggers("runtime-1")
        assert triggers is not None
        assert len(triggers) == 1
        assert triggers[0].trigger_type == UiPathResumeTriggerType.QUEUE_ITEM
        assert triggers[0].trigger_name == UiPathResumeTriggerName.QUEUE_ITEM
        assert triggers[0].item_key == "queue-123"

    @pytest.mark.asyncio
    async def test_save_trigger_with_api_type(self, storage: SqliteAgentStorage):
        """Test saving an API type trigger."""
        trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.API,
            trigger_name=UiPathResumeTriggerName.API.value,
            item_key="inbox-789",
            folder_path="/api/folder",
            folder_key="folder-abc",
            payload='{"request": "data"}',
            interrupt_id="interrupt-123",
        )
        trigger.api_resume = UiPathApiTrigger(
            inbox_id="inbox-789", request='{"request": "data"}'
        )

        await storage.save_triggers("runtime-2", [trigger])

        retrieved = await storage.get_triggers("runtime-2")
        assert retrieved is not None
        assert len(retrieved) == 1
        assert retrieved[0].trigger_type == UiPathResumeTriggerType.API
        assert retrieved[0].api_resume is not None
        assert retrieved[0].api_resume.inbox_id == "inbox-789"

    @pytest.mark.asyncio
    async def test_save_multiple_triggers(self, storage: SqliteAgentStorage):
        """Test saving multiple triggers for the same runtime."""
        trigger1 = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="first",
            interrupt_id="interrupt-1",
        )
        trigger2 = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="second",
            interrupt_id="interrupt-2",
        )

        await storage.save_triggers("runtime-5", [trigger1, trigger2])

        retrieved = await storage.get_triggers("runtime-5")
        assert retrieved is not None
        assert len(retrieved) == 2
        assert retrieved[0].item_key == "first"
        assert retrieved[1].item_key == "second"

    @pytest.mark.asyncio
    async def test_save_triggers_replaces_existing(self, storage: SqliteAgentStorage):
        """Test that saving triggers replaces existing ones."""
        trigger1 = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="first",
            interrupt_id="interrupt-1",
        )
        trigger2 = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="second",
            interrupt_id="interrupt-2",
        )

        await storage.save_triggers("runtime-3", [trigger1])
        await storage.save_triggers("runtime-3", [trigger2])

        retrieved = await storage.get_triggers("runtime-3")
        assert retrieved is not None
        assert len(retrieved) == 1
        assert retrieved[0].item_key == "second"

    @pytest.mark.asyncio
    async def test_get_triggers_nonexistent(self, storage: SqliteAgentStorage):
        """Test getting trigger for non-existent runtime_id."""
        result = await storage.get_triggers("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_trigger(self, storage: SqliteAgentStorage):
        """Test deleting a specific trigger."""
        trigger1 = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="keep",
            interrupt_id="interrupt-keep",
        )
        trigger2 = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="delete",
            interrupt_id="interrupt-delete",
        )

        await storage.save_triggers("runtime-del", [trigger1, trigger2])

        # Delete one trigger
        await storage.delete_trigger("runtime-del", trigger2)

        retrieved = await storage.get_triggers("runtime-del")
        assert retrieved is not None
        assert len(retrieved) == 1
        assert retrieved[0].item_key == "keep"


class TestStateOperations:
    """Test agent state save and load operations."""

    @pytest.fixture
    async def storage(self):
        """Create a SqliteAgentStorage instance with temporary database file."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        try:
            async with SqliteAgentStorage(str(temp_db.name)) as storage:
                await storage.setup()
                yield storage
        finally:
            if os.path.exists(temp_db.name):
                os.remove(temp_db.name)

    @pytest.mark.asyncio
    async def test_save_and_load_state_basic(self, storage: SqliteAgentStorage):
        """Test saving and loading a basic state."""
        state = {"step": 1, "data": "test data", "flags": {"active": True}}

        await storage.save_state("runtime-1", state)
        loaded = await storage.load_state("runtime-1")

        assert loaded == state

    @pytest.mark.asyncio
    async def test_save_and_load_state_complex(self, storage: SqliteAgentStorage):
        """Test saving and loading complex state with nested structures."""
        state = {
            "variables": {"counter": 42, "name": "test", "items": [1, 2, 3, 4, 5]},
            "agent_state": {
                "current_step": "processing",
                "metadata": {"created": "2024-01-01", "tags": ["tag1", "tag2"]},
            },
        }

        await storage.save_state("runtime-2", state)
        loaded = await storage.load_state("runtime-2")

        assert loaded == state

    @pytest.mark.asyncio
    async def test_save_state_overwrites_existing(self, storage: SqliteAgentStorage):
        """Test that saving state overwrites existing state."""
        state1 = {"step": 1}
        state2 = {"step": 2, "new_field": "value"}

        await storage.save_state("runtime-3", state1)
        await storage.save_state("runtime-3", state2)

        loaded = await storage.load_state("runtime-3")
        assert loaded == state2
        assert loaded != state1

    @pytest.mark.asyncio
    async def test_load_state_nonexistent(self, storage: SqliteAgentStorage):
        """Test loading state for non-existent runtime_id."""
        result = await storage.load_state("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_state_empty_dict(self, storage: SqliteAgentStorage):
        """Test saving empty dictionary as state."""
        state: dict[str, Any] = {}

        await storage.save_state("runtime-4", state)
        loaded = await storage.load_state("runtime-4")

        assert loaded == {}


class TestKeyValueOperations:
    """Test key-value storage operations."""

    @pytest.fixture
    async def storage(self):
        """Create a SqliteAgentStorage instance with temporary database file."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        try:
            async with SqliteAgentStorage(str(temp_db.name)) as storage:
                await storage.setup()
                yield storage
        finally:
            if os.path.exists(temp_db.name):
                os.remove(temp_db.name)

    @pytest.mark.asyncio
    async def test_set_and_get_string_value(self, storage: SqliteAgentStorage):
        """Test setting and getting a string value."""
        await storage.set_value("runtime-1", "namespace1", "key1", "test_value")

        value = await storage.get_value("runtime-1", "namespace1", "key1")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_set_and_get_dict_value(self, storage: SqliteAgentStorage):
        """Test setting and getting a dictionary value."""
        test_dict = {"name": "John", "age": 30, "active": True}

        await storage.set_value("runtime-2", "namespace2", "key2", test_dict)

        value = await storage.get_value("runtime-2", "namespace2", "key2")
        assert value == test_dict

    @pytest.mark.asyncio
    async def test_set_and_get_pydantic_model(self, storage: SqliteAgentStorage):
        """Test setting and getting a Pydantic model."""
        model = SampleModel(name="test", value=42)

        await storage.set_value("runtime-3", "namespace3", "key3", model)

        value = await storage.get_value("runtime-3", "namespace3", "key3")
        assert value == model.model_dump()

    @pytest.mark.asyncio
    async def test_set_and_get_none_value(self, storage: SqliteAgentStorage):
        """Test setting and getting None value."""
        await storage.set_value("runtime-4", "namespace4", "key4", None)

        value = await storage.get_value("runtime-4", "namespace4", "key4")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_value_invalid_type(self, storage: SqliteAgentStorage):
        """Test that setting invalid type raises TypeError."""
        with pytest.raises(
            TypeError, match="Value must be str, dict, BaseModel or None"
        ):
            await storage.set_value("runtime-5", "namespace5", "key5", 123)

        with pytest.raises(
            TypeError, match="Value must be str, dict, BaseModel or None"
        ):
            await storage.set_value("runtime-5", "namespace5", "key5", [1, 2, 3])

    @pytest.mark.asyncio
    async def test_set_value_overwrites_existing(self, storage: SqliteAgentStorage):
        """Test that setting a value overwrites existing value."""
        await storage.set_value("runtime-6", "namespace6", "key6", "first")
        await storage.set_value("runtime-6", "namespace6", "key6", "second")

        value = await storage.get_value("runtime-6", "namespace6", "key6")
        assert value == "second"

    @pytest.mark.asyncio
    async def test_get_value_nonexistent(self, storage: SqliteAgentStorage):
        """Test getting non-existent value returns None."""
        value = await storage.get_value("nonexistent", "namespace", "key")
        assert value is None

    @pytest.mark.asyncio
    async def test_values_isolated_by_runtime_id(self, storage: SqliteAgentStorage):
        """Test that values are isolated by runtime_id."""
        await storage.set_value("runtime-a", "ns", "key", "value-a")
        await storage.set_value("runtime-b", "ns", "key", "value-b")

        value_a = await storage.get_value("runtime-a", "ns", "key")
        value_b = await storage.get_value("runtime-b", "ns", "key")

        assert value_a == "value-a"
        assert value_b == "value-b"

    @pytest.mark.asyncio
    async def test_values_isolated_by_namespace(self, storage: SqliteAgentStorage):
        """Test that values are isolated by namespace."""
        await storage.set_value("runtime-1", "ns-a", "key", "value-a")
        await storage.set_value("runtime-1", "ns-b", "key", "value-b")

        value_a = await storage.get_value("runtime-1", "ns-a", "key")
        value_b = await storage.get_value("runtime-1", "ns-b", "key")

        assert value_a == "value-a"
        assert value_b == "value-b"


class TestSerializationMethods:
    """Test internal serialization/deserialization methods."""

    @pytest.fixture
    async def storage(self):
        """Create a SqliteAgentStorage instance with temporary database file."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        try:
            async with SqliteAgentStorage(str(temp_db.name)) as storage:
                await storage.setup()
                yield storage
        finally:
            if os.path.exists(temp_db.name):
                os.remove(temp_db.name)

    def test_serialize_trigger_queue_type(self, storage: SqliteAgentStorage):
        """Test serialization of queue type trigger."""
        trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="queue-123",
            folder_path="/folder",
            folder_key="folder-key",
            payload={"test": "data"},
            interrupt_id="interrupt-456",
        )

        serialized = storage._serialize_trigger(trigger)

        assert serialized["type"] == UiPathResumeTriggerType.QUEUE_ITEM.value
        assert serialized["key"] == "queue-123"
        assert serialized["name"] == UiPathResumeTriggerName.QUEUE_ITEM.value
        assert serialized["folder_path"] == "/folder"
        assert serialized["folder_key"] == "folder-key"
        assert serialized["interrupt_id"] == "interrupt-456"
        assert json.loads(serialized["payload"]) == {"test": "data"}

    def test_deserialize_trigger_queue_type(self, storage: SqliteAgentStorage):
        """Test deserialization of queue type trigger."""
        trigger_data = {
            "type": UiPathResumeTriggerType.QUEUE_ITEM.value,
            "key": "queue-789",
            "name": UiPathResumeTriggerName.QUEUE_ITEM.value,
            "folder_path": "/test",
            "folder_key": "folder-123",
            "payload": '{"key": "value"}',
        }

        trigger = storage._deserialize_trigger(trigger_data)

        assert trigger.trigger_type == UiPathResumeTriggerType.QUEUE_ITEM
        assert trigger.trigger_name == UiPathResumeTriggerName.QUEUE_ITEM
        assert trigger.item_key == "queue-789"
        assert trigger.folder_path == "/test"
        assert trigger.folder_key == "folder-123"

    def test_dump_value_string(self, storage: SqliteAgentStorage):
        """Test _dump_value with string."""
        result = storage._dump_value("test string")
        assert result == "s:test string"

    def test_dump_value_dict(self, storage: SqliteAgentStorage):
        """Test _dump_value with dictionary."""
        result = storage._dump_value({"key": "value"})
        assert result == 'j:{"key": "value"}'

    def test_dump_value_pydantic_model(self, storage: SqliteAgentStorage):
        """Test _dump_value with Pydantic model."""
        model = SampleModel(name="test", value=42)
        result = storage._dump_value(model)
        assert result == 'j:{"name": "test", "value": 42}'

    def test_dump_value_none(self, storage: SqliteAgentStorage):
        """Test _dump_value with None."""
        result = storage._dump_value(None)
        assert result is None

    def test_load_value_string(self, storage: SqliteAgentStorage):
        """Test _load_value with string."""
        result = storage._load_value("s:test string")
        assert result == "test string"

    def test_load_value_json(self, storage: SqliteAgentStorage):
        """Test _load_value with JSON."""
        result = storage._load_value('j:{"key": "value"}')
        assert result == {"key": "value"}

    def test_load_value_none(self, storage: SqliteAgentStorage):
        """Test _load_value with None."""
        result = storage._load_value(None)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
