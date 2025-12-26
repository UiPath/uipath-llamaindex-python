"""Additional integration and edge case tests for SQLiteResumableStorage."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from uipath.runtime import (
    UiPathResumeTrigger,
    UiPathResumeTriggerName,
    UiPathResumeTriggerType,
)

from uipath_llamaindex.runtime.storage import SQLiteResumableStorage


class ComplexModel(BaseModel):
    """Complex nested Pydantic model for testing."""

    id: str
    data: dict[str, Any]
    items: list[Any]
    nested: dict[str, Any]


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    async def storage(self, tmp_path: Path):
        """Create and setup a storage instance."""
        db_path = tmp_path / "integration_test.db"
        storage = SQLiteResumableStorage(str(db_path))
        await storage.setup()
        return storage

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self, storage: SQLiteResumableStorage):
        """Test a complete workflow lifecycle with all storage operations."""
        runtime_id = "workflow-123"

        # 1. Save initial trigger
        initial_trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="queue-item-1",
            folder_path="/production",
            folder_key="prod-folder",
            payload={"order_id": "12345"},
            interrupt_id="interrupt-12345",
        )
        await storage.save_triggers(runtime_id, [initial_trigger])

        # 2. Save workflow context
        context = {
            "current_step": "processing_order",
            "order_id": "12345",
            "customer_data": {"name": "John Doe", "email": "john@example.com"},
            "items": ["item1", "item2", "item3"],
            "total_amount": 299.99,
        }
        await storage.save_context(runtime_id, context)

        # 3. Save some KV pairs
        await storage.set_value(
            runtime_id, "metadata", "processed_at", "2024-01-15T10:30:00Z"
        )
        await storage.set_value(runtime_id, "status", "current", "in_progress")
        await storage.set_value(runtime_id, "metrics", "retry_count", "0")

        # 4. Update workflow context (simulating workflow progress)
        updated_context = context.copy()
        updated_context["current_step"] = "awaiting_approval"
        updated_context["approval_requested_at"] = "2024-01-15T10:35:00Z"
        await storage.save_context(runtime_id, updated_context)

        # 5. Save resume trigger (simulating workflow suspension)
        resume_trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.API,
            trigger_name=UiPathResumeTriggerName.API.value,
            item_key="approval-inbox-789",
            payload='{"approval_status": "pending"}',
            interrupt_id="interrupt-12345",
        )
        await storage.save_triggers(runtime_id, [resume_trigger])

        # 6. Verify all data can be retrieved
        triggers = await storage.get_triggers(runtime_id)
        loaded_context = await storage.load_context(runtime_id)
        processed_at = await storage.get_value(runtime_id, "metadata", "processed_at")
        status = await storage.get_value(runtime_id, "status", "current")

        assert triggers is not None
        trigger = triggers[0]
        assert trigger is not None
        assert trigger.trigger_type == UiPathResumeTriggerType.API
        assert trigger.item_key == "approval-inbox-789"
        assert loaded_context is not None
        assert loaded_context["current_step"] == "awaiting_approval"
        assert processed_at == "2024-01-15T10:30:00Z"
        assert status == "in_progress"

    @pytest.mark.asyncio
    async def test_multiple_parallel_workflows(self, storage: SQLiteResumableStorage):
        """Test handling multiple parallel workflows."""
        workflows: list[tuple[str, UiPathResumeTrigger | None, dict[str, Any]]] = []
        trigger: UiPathResumeTrigger | None
        context: dict[str, Any] | None

        # Create multiple parallel workflows
        for i in range(10):
            runtime_id = f"workflow-{i}"

            trigger = UiPathResumeTrigger(
                trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
                trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
                item_key=f"queue-item-{i}",
                interrupt_id=f"interrupt-{i}",
            )

            context = {
                "workflow_id": i,
                "data": f"data-{i}",
                "step": i % 3,  # Distribute across 3 steps
            }

            workflows.append((runtime_id, trigger, context))

        # Save all workflows concurrently
        save_tasks = []
        for runtime_id, trigger, context in workflows:
            assert trigger is not None
            save_tasks.append(storage.save_triggers(runtime_id, [trigger]))
            save_tasks.append(storage.save_context(runtime_id, context))
            save_tasks.append(storage.set_value(runtime_id, "meta", "status", "active"))

        await asyncio.gather(*save_tasks)

        # Verify all workflows were saved correctly
        for runtime_id, expected_trigger, expected_context in workflows:
            triggers = await storage.get_triggers(runtime_id)
            context = await storage.load_context(runtime_id)
            status = await storage.get_value(runtime_id, "meta", "status")

            assert expected_trigger is not None
            assert triggers is not None
            assert triggers[0] is not None
            assert triggers[0].item_key == expected_trigger.item_key
            assert context == expected_context
            assert status == "active"

    @pytest.mark.asyncio
    async def test_workflow_state_updates(self, storage: SQLiteResumableStorage):
        """Test updating workflow state multiple times."""
        runtime_id = "stateful-workflow"

        # Simulate workflow progressing through multiple states
        states = [
            {"step": "initialize", "progress": 0},
            {"step": "validate", "progress": 25},
            {"step": "process", "progress": 50},
            {"step": "verify", "progress": 75},
            {"step": "complete", "progress": 100},
        ]

        for state in states:
            await storage.save_context(runtime_id, state)
            await storage.set_value(
                runtime_id, "workflow", "last_update", state["step"]
            )

        # Final state should be the last one
        final_context = await storage.load_context(runtime_id)
        last_update = await storage.get_value(runtime_id, "workflow", "last_update")

        assert final_context == {"step": "complete", "progress": 100}
        assert last_update == "complete"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    async def storage(self, tmp_path: Path):
        """Create and setup a storage instance."""
        db_path = tmp_path / "edge_test.db"
        storage = SQLiteResumableStorage(str(db_path))
        await storage.setup()
        return storage

    @pytest.mark.asyncio
    async def test_very_large_context(self, storage: SQLiteResumableStorage):
        """Test handling of very large context data."""
        runtime_id = "large-context"

        # Create a large context with many keys
        large_context = {
            f"key_{i}": f"value_{i}" * 100  # Each value is ~600 bytes
            for i in range(1000)  # 1000 keys
        }

        await storage.save_context(runtime_id, large_context)
        loaded = await storage.load_context(runtime_id)

        assert loaded is not None
        assert len(loaded) == 1000
        assert loaded["key_0"] == "value_0" * 100

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(
        self, storage: SQLiteResumableStorage
    ):
        """Test handling of Unicode and special characters."""
        runtime_id = "unicode-test"

        # Test various Unicode characters
        context = {
            "chinese": "你好世界",
            "japanese": "こんにちは",
            "emoji": "😀🎉🚀",
            "arabic": "مرحبا",
            "special": "!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/",
        }

        await storage.save_context(runtime_id, context)
        loaded = await storage.load_context(runtime_id)

        assert loaded == context

    @pytest.mark.asyncio
    async def test_empty_string_values(self, storage: SQLiteResumableStorage):
        """Test handling of empty strings."""
        runtime_id = "empty-strings"

        await storage.set_value(runtime_id, "ns", "empty", "")
        value = await storage.get_value(runtime_id, "ns", "empty")

        assert value == ""

    @pytest.mark.asyncio
    async def test_whitespace_only_values(self, storage: SQLiteResumableStorage):
        """Test handling of whitespace-only strings."""
        runtime_id = "whitespace"

        test_values = [
            "   ",  # spaces
            "\t\t",  # tabs
            "\n\n",  # newlines
            " \t\n ",  # mixed
        ]

        for i, val in enumerate(test_values):
            await storage.set_value(runtime_id, "ws", f"key{i}", val)

        for i, expected in enumerate(test_values):
            value = await storage.get_value(runtime_id, "ws", f"key{i}")
            assert value == expected

    @pytest.mark.asyncio
    async def test_nested_dict_with_none_values(self, storage: SQLiteResumableStorage):
        """Test handling of nested dictionaries with None values."""
        runtime_id = "nested-none"

        nested = {
            "level1": {"level2": {"value": None, "other": "data"}, "another": None},
            "top_none": None,
        }

        await storage.save_context(runtime_id, nested)
        loaded = await storage.load_context(runtime_id)

        assert loaded == nested

    @pytest.mark.asyncio
    async def test_very_long_runtime_id(self, storage: SQLiteResumableStorage):
        """Test handling of very long runtime IDs."""
        runtime_id = "a" * 500  # Very long runtime ID

        trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="test-key",
            interrupt_id="interrupt-long",
        )

        await storage.save_triggers(runtime_id, [trigger])
        triggers = await storage.get_triggers(runtime_id)

        assert triggers is not None
        assert triggers[0] is not None
        assert triggers[0].item_key == "test-key"

    @pytest.mark.asyncio
    async def test_special_characters_in_keys(self, storage: SQLiteResumableStorage):
        """Test handling of special characters in namespace and key names."""
        runtime_id = "special-chars"

        # Test various special characters
        test_cases = [
            ("namespace-with-dashes", "key-with-dashes"),
            ("namespace_with_underscores", "key_with_underscores"),
            ("namespace.with.dots", "key.with.dots"),
            ("namespace:with:colons", "key:with:colons"),
        ]

        for ns, key in test_cases:
            await storage.set_value(runtime_id, ns, key, f"value-{ns}-{key}")

        for ns, key in test_cases:
            value = await storage.get_value(runtime_id, ns, key)
            assert value == f"value-{ns}-{key}"

    @pytest.mark.asyncio
    async def test_json_with_escaped_characters(self, storage: SQLiteResumableStorage):
        """Test handling of JSON with escaped characters."""
        runtime_id = "escaped-json"

        data = {
            "quoted": 'String with "quotes"',
            "backslash": "Path\\to\\file",
            "newline": "Line1\nLine2",
            "tab": "Col1\tCol2",
        }

        await storage.set_value(runtime_id, "ns", "json", data)
        retrieved = await storage.get_value(runtime_id, "ns", "json")

        assert retrieved == data

    @pytest.mark.asyncio
    async def test_deeply_nested_structures(self, storage: SQLiteResumableStorage):
        """Test handling of deeply nested data structures."""
        runtime_id = "deep-nest"

        # Create a deeply nested structure
        def create_nested(depth):
            if depth == 0:
                return "leaf"
            return {"level": depth, "child": create_nested(depth - 1)}

        deep_structure = create_nested(20)

        await storage.save_context(runtime_id, {"root": deep_structure})
        loaded = await storage.load_context(runtime_id)

        assert loaded == {"root": deep_structure}

    @pytest.mark.asyncio
    async def test_trigger_with_complex_payload(self, storage: SQLiteResumableStorage):
        """Test trigger with complex nested payload."""
        runtime_id = "complex-payload"

        complex_payload = {
            "transaction": {
                "id": "tx-12345",
                "items": [
                    {"sku": "ITEM-001", "quantity": 2, "price": 29.99},
                    {"sku": "ITEM-002", "quantity": 1, "price": 49.99},
                ],
                "customer": {
                    "id": "CUST-789",
                    "address": {
                        "street": "123 Main St",
                        "city": "Springfield",
                        "country": "US",
                    },
                },
                "metadata": {
                    "tags": ["priority", "express"],
                    "notes": "Handle with care",
                },
            }
        }

        trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType.QUEUE_ITEM,
            trigger_name=UiPathResumeTriggerName.QUEUE_ITEM.value,
            item_key="complex-item",
            payload=complex_payload,
            interrupt_id="interrupt-complex",
        )

        await storage.save_triggers(runtime_id, [trigger])
        triggers = await storage.get_triggers(runtime_id)

        assert triggers is not None
        assert triggers[0] is not None
        assert isinstance(triggers[0].payload, str)
        # Payload gets JSON serialized and deserialized
        assert json.loads(triggers[0].payload) == complex_payload


class TestDataConsistency:
    """Test data consistency and isolation."""

    @pytest.fixture
    async def storage(self, tmp_path: Path):
        """Create and setup a storage instance."""
        db_path = tmp_path / "consistency_test.db"
        storage = SQLiteResumableStorage(str(db_path))
        await storage.setup()
        return storage

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, storage: SQLiteResumableStorage):
        """Test concurrent reads of the same data."""
        runtime_id = "concurrent-read-test"

        context = {"data": "test", "value": 42}
        await storage.save_context(runtime_id, context)

        # Perform multiple concurrent reads
        results = await asyncio.gather(
            *[storage.load_context(runtime_id) for _ in range(20)]
        )

        # All reads should return the same data
        for result in results:
            assert result == context

    @pytest.mark.asyncio
    async def test_kv_isolation_stress_test(self, storage: SQLiteResumableStorage):
        """Stress test KV store isolation."""
        tasks = []

        # Create many KV operations with different combinations
        for runtime in range(5):
            for namespace in range(5):
                for key in range(5):
                    tasks.append(
                        storage.set_value(
                            f"runtime-{runtime}",
                            f"ns-{namespace}",
                            f"key-{key}",
                            f"value-{runtime}-{namespace}-{key}",
                        )
                    )

        await asyncio.gather(*tasks)

        # Verify each value is correctly isolated
        for runtime in range(5):
            for namespace in range(5):
                for key in range(5):
                    value = await storage.get_value(
                        f"runtime-{runtime}", f"ns-{namespace}", f"key-{key}"
                    )
                    expected = f"value-{runtime}-{namespace}-{key}"
                    assert value == expected, f"Expected {expected}, got {value}"

    @pytest.mark.asyncio
    async def test_update_race_condition(self, storage: SQLiteResumableStorage):
        """Test that concurrent updates don't cause data corruption."""
        runtime_id = "race-condition-test"

        # Initialize with a value
        await storage.set_value(runtime_id, "counter", "value", "0")

        # Simulate concurrent updates (not a real increment, just updates)
        async def update_value(suffix):
            await storage.set_value(runtime_id, "counter", "value", f"updated-{suffix}")

        await asyncio.gather(*[update_value(i) for i in range(10)])

        # Final value should be one of the updates (last write wins)
        final_value: str = await storage.get_value(runtime_id, "counter", "value")
        assert final_value.startswith("updated-")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
