"""SQLite implementation of UiPathResumableStorageProtocol."""

import json
import os
import pickle
from typing import Any

import aiosqlite
from uipath.core.errors import ErrorCategory, UiPathFaultedTriggerError
from uipath.runtime import (
    UiPathApiTrigger,
    UiPathResumeTrigger,
    UiPathResumeTriggerName,
    UiPathResumeTriggerType,
)


class SQLiteResumableStorage:
    """SQLite database storage for resume triggers and workflow context."""

    def __init__(self, storage_path: str):
        """
        Initialize SQLite storage.

        Args:
            storage_path: Path to the SQLite database file
        """
        self.storage_path = storage_path

    async def setup(self) -> None:
        """Ensure storage directory and database tables exist."""
        dir_name = os.path.dirname(self.storage_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        try:
            async with aiosqlite.connect(self.storage_path) as conn:
                # Table for workflow contexts
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_contexts (
                        runtime_id TEXT PRIMARY KEY,
                        context_data BLOB NOT NULL
                    )
                """)

                # Table for resume triggers
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS resume_triggers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trigger_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                await conn.commit()
        except aiosqlite.Error as exc:
            msg = f"Failed to initialize SQLite storage at {self.storage_path!r}: {exc.sqlite_errorname} {exc.sqlite_errorcode}"
            raise UiPathFaultedTriggerError(ErrorCategory.SYSTEM, msg) from exc

    async def save_trigger(self, trigger: UiPathResumeTrigger) -> None:
        """Save resume trigger to SQLite database."""
        trigger_dict = self._serialize_trigger(trigger)
        trigger_json = json.dumps(trigger_dict)

        try:
            async with aiosqlite.connect(self.storage_path) as conn:
                await conn.execute(
                    "INSERT INTO resume_triggers (trigger_data) VALUES (?)",
                    (trigger_json,),
                )
                await conn.commit()
        except aiosqlite.Error as exc:
            msg = (
                f"Failed to save resume trigger "
                f"(type={trigger.trigger_type}, name={trigger.trigger_name}) "
                f"to database {self.storage_path!r}:"
                f" {exc.sqlite_errorname} {exc.sqlite_errorcode}"
            )
            raise UiPathFaultedTriggerError(ErrorCategory.SYSTEM, msg) from exc

    async def get_latest_trigger(self) -> UiPathResumeTrigger | None:
        """Get most recent trigger from SQLite database."""
        try:
            async with aiosqlite.connect(self.storage_path) as conn:
                cursor = await conn.execute(
                    "SELECT trigger_data FROM resume_triggers ORDER BY created_at DESC LIMIT 1"
                )
                row = await cursor.fetchone()
        except aiosqlite.Error as exc:
            msg = f"Failed to retrieve latest resume trigger from database {self.storage_path!r}: {exc.sqlite_errorname} {exc.sqlite_errorcode}"
            raise UiPathFaultedTriggerError(ErrorCategory.SYSTEM, msg) from exc

        if not row:
            return None

        trigger_dict = json.loads(row[0])
        return self._deserialize_trigger(trigger_dict)

    async def save_context(self, runtime_id: str, context_dict: dict[str, Any]) -> None:
        """
        Save workflow context to SQLite database.

        Args:
            runtime_id: Unique identifier for the runtime instance
            context_dict: Serialized workflow context dictionary
        """
        context_blob = pickle.dumps(context_dict)

        try:
            async with aiosqlite.connect(self.storage_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO workflow_contexts (runtime_id, context_data)
                    VALUES (?, ?)
                    ON CONFLICT(runtime_id) DO UPDATE SET
                        context_data = excluded.context_data
                    """,
                    (runtime_id, context_blob),
                )
                await conn.commit()
        except aiosqlite.Error as exc:
            msg = f"Failed to save workflow context to database {self.storage_path!r}: {exc.sqlite_errorname} {exc.sqlite_errorcode}"
            raise UiPathFaultedTriggerError(ErrorCategory.SYSTEM, msg) from exc

    async def load_context(self, runtime_id: str) -> dict[str, Any] | None:
        """
        Load workflow context from SQLite database.

        Args:
            runtime_id: Unique identifier for the runtime instance

        Returns:
            Serialized workflow context dictionary or None if not found
        """
        try:
            async with aiosqlite.connect(self.storage_path) as conn:
                cursor = await conn.execute(
                    "SELECT context_data FROM workflow_contexts WHERE runtime_id = ?",
                    (runtime_id,),
                )
                row = await cursor.fetchone()
        except aiosqlite.Error as exc:
            msg = f"Failed to load workflow context from database {self.storage_path!r}: {exc.sqlite_errorname} {exc.sqlite_errorcode}"
            raise UiPathFaultedTriggerError(ErrorCategory.SYSTEM, msg) from exc

        if not row:
            return None

        return pickle.loads(row[0])

    def _serialize_trigger(self, trigger: UiPathResumeTrigger) -> dict[str, Any]:
        """Serialize a resume trigger to a dictionary."""
        trigger_key = (
            trigger.api_resume.inbox_id if trigger.api_resume else trigger.item_key
        )
        payload = (
            json.dumps(trigger.payload)
            if isinstance(trigger.payload, dict)
            else str(trigger.payload)
            if trigger.payload
            else None
        )

        return {
            "type": trigger.trigger_type.value,
            "key": trigger_key,
            "name": trigger.trigger_name.value,
            "payload": payload,
            "folder_path": trigger.folder_path,
            "folder_key": trigger.folder_key,
        }

    def _deserialize_trigger(self, trigger_data: dict[str, Any]) -> UiPathResumeTrigger:
        """Deserialize a resume trigger from a dictionary."""
        trigger_type = trigger_data["type"]
        key = trigger_data["key"]
        name = trigger_data["name"]
        folder_path = trigger_data.get("folder_path")
        folder_key = trigger_data.get("folder_key")
        payload = trigger_data.get("payload")

        resume_trigger = UiPathResumeTrigger(
            trigger_type=UiPathResumeTriggerType(trigger_type),
            trigger_name=UiPathResumeTriggerName(name),
            item_key=key,
            folder_path=folder_path,
            folder_key=folder_key,
            payload=payload,
        )

        if resume_trigger.trigger_type == UiPathResumeTriggerType.API:
            resume_trigger.api_resume = UiPathApiTrigger(
                inbox_id=resume_trigger.item_key, request=resume_trigger.payload
            )

        return resume_trigger
