import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class LlamaConfig:
    def __init__(self, config_path: str = "llama.json"):
        self.config_path = config_path

        if self.exists:
            self._load_config()

    @property
    def exists(self) -> bool:
        """Check if llama.json exists"""
        return os.path.exists(self.config_path)

    def _load_config(self) -> None:
        """Load and process Llama agent configuration."""
        try:
            with open(self.config_path, "r") as f:
                self._raw_config = json.load(f)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.config_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to load llama.json: {str(e)}")
            raise

    def load_config(self) -> Dict[str, Any]:
        """Load and validate Llama agents configuration."""
        if not self.exists:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        self._load_config()
        return self._raw_config
