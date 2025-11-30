"""Pickle implementation of UiPathResumableStorageProtocol."""

import json
import os
import pickle
from typing import Any

from uipath.runtime import (
    UiPathApiTrigger,
    UiPathResumeTrigger,
    UiPathResumeTriggerName,
    UiPathResumeTriggerType,
)


class PickleResumableStorage:
    """Pickle file storage for resume triggers and workflow context."""

    def __init__(self, storage_path: str):
        """
        Initialize pickle storage.

        Args:
            storage_path: Path to the pickle file for storing state
        """
        self.storage_path = storage_path
        self._initialized = False

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists."""
        if self._initialized:
            return

        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self._initialized = True

    async def save_trigger(self, trigger: UiPathResumeTrigger) -> None:
        """Save resume trigger to pickle file."""
        self._ensure_storage()

        data = self._load_data()

        data["resume_trigger"] = self._serialize_trigger(trigger)

        self._save_data(data)

    async def get_latest_trigger(self) -> UiPathResumeTrigger | None:
        """Get most recent trigger from pickle file."""
        self._ensure_storage()

        if not os.path.exists(self.storage_path):
            return None

        data = self._load_data()
        trigger_data = data.get("resume_trigger")

        if not trigger_data:
            return None

        return self._deserialize_trigger(trigger_data)

    def save_context(self, context_dict: dict[str, Any]) -> None:
        """
        Save workflow context to pickle file.

        Args:
            context_dict: Serialized workflow context dictionary
        """
        self._ensure_storage()

        data = self._load_data()

        data["workflow_context"] = context_dict

        self._save_data(data)

    def load_context(self) -> dict[str, Any] | None:
        """
        Load workflow context from pickle file.

        Returns:
            Serialized workflow context dictionary or None if not found
        """
        self._ensure_storage()

        if not os.path.exists(self.storage_path):
            return None

        data = self._load_data()
        return data.get("workflow_context")

    def _load_data(self) -> dict[str, Any]:
        """Load data from pickle file."""
        if not os.path.exists(self.storage_path):
            return {}

        with open(self.storage_path, "rb") as f:
            return pickle.load(f)

    def _save_data(self, data: dict[str, Any]) -> None:
        """Save data to pickle file."""
        with open(self.storage_path, "wb") as f:
            pickle.dump(data, f)

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
