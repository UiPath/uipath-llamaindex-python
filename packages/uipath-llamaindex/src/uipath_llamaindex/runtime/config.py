"""Simple loader for llama_index.json configuration."""

import json
import os


class LlamaIndexConfig:
    """Simple loader for llama_index.json configuration."""

    def __init__(self, config_path: str = "llama_index.json"):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to llama_index.json file
        """
        self.config_path = config_path
        self._workflows: dict[str, str] | None = None

    @property
    def exists(self) -> bool:
        """Check if llama_index.json exists."""
        return os.path.exists(self.config_path)

    @property
    def workflows(self) -> dict[str, str]:
        """
        Get workflow name -> path mapping from config.

        Returns:
            Dictionary mapping workflow names to file paths (e.g., {"agent": "agent.py:workflow"})
        """
        if self._workflows is None:
            self._workflows = self._load_workflows()
        return self._workflows

    def _load_workflows(self) -> dict[str, str]:
        """Load workflow definitions from llama_index.json."""
        if not self.exists:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)

            if "workflows" not in config:
                raise ValueError(
                    "Missing required 'workflows' field in llama_index.json"
                )

            workflows = config["workflows"]
            if not isinstance(workflows, dict):
                raise ValueError("'workflows' must be a dictionary")

            return workflows

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.config_path}: {e}") from e

    @property
    def entrypoints(self) -> list[str]:
        """Get list of available workflow entrypoints."""
        return list(self.workflows.keys())
