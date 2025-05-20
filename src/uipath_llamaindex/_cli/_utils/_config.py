import importlib.util
import inspect
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from llama_index.core.workflow import Workflow

logger = logging.getLogger(__name__)


@dataclass
class WorkflowConfig:
    name: str
    path: str
    file_path: str
    workflow_var: str
    _workflow: Optional[Workflow] = None

    @classmethod
    def from_config(cls, name: str, path: str) -> "WorkflowConfig":
        file_path, workflow_var = path.split(":")
        return cls(name=name, path=path, file_path=file_path, workflow_var=workflow_var)

    async def load_workflow(self) -> Workflow:
        """Load workflow from the specified path"""
        try:
            cwd = os.path.abspath(os.getcwd())
            abs_file_path = os.path.abspath(os.path.normpath(self.file_path))

            if not abs_file_path.startswith(cwd):
                raise ValueError(
                    f"Script path must be within the current directory. Found: {self.file_path}"
                )

            if not os.path.exists(abs_file_path):
                raise FileNotFoundError(f"Script not found: {abs_file_path}")

            if cwd not in sys.path:
                sys.path.insert(0, cwd)

            module_name = Path(abs_file_path).stem
            spec = importlib.util.spec_from_file_location(module_name, abs_file_path)

            if not spec or not spec.loader:
                raise ImportError(f"Could not load module from: {abs_file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Get the workflow object or function
            workflow_obj = getattr(module, self.workflow_var, None)

            # Handle callable workflow factory
            if callable(workflow_obj) and not isinstance(workflow_obj, Workflow):
                if inspect.iscoroutinefunction(workflow_obj):
                    # Handle async function
                    try:
                        workflow_obj = await workflow_obj()
                    except RuntimeError as e:
                        raise e
                else:
                    # Call regular function
                    workflow_obj = workflow_obj()

            # Handle async context manager
            if (
                workflow_obj is not None
                and hasattr(workflow_obj, "__aenter__")
                and callable(workflow_obj.__aenter__)
            ):
                self._context_manager = workflow_obj
                workflow = await workflow_obj.__aenter__()
            else:
                # Not a context manager, use directly
                workflow = workflow_obj

            if not isinstance(workflow, Workflow):
                raise TypeError(
                    f"Expected Workflow or a callable returning a Workflow, got {type(workflow)}"
                )

            self._workflow = workflow
            return workflow

        except Exception as e:
            logger.error(f"Failed to load workflow {self.name}: {str(e)}")
            raise

    async def cleanup(self):
        """
        Clean up resources when done with the workflow.
        This should be called when the workflow is no longer needed.
        """
        if hasattr(self, "_context_manager") and self._context_manager:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error during context cleanup: {str(e)}")
            finally:
                self._context_manager = None
                self._workflow = None


class LlamaIndexConfig:
    def __init__(self, config_path: str = "llama_index.json"):
        self.config_path = config_path
        self._config: Optional[Dict[str, Any]] = None
        self._workflows: List[WorkflowConfig] = []

    @property
    def exists(self) -> bool:
        """Check if llama_index.json exists"""
        return os.path.exists(self.config_path)

    def load_config(self) -> Dict[str, Any]:
        """Load and validate LlamaIndex workflow configuration"""
        if not self.exists:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)

            required_fields = ["workflows"]
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                raise ValueError(
                    f"Missing required fields in llama_index.json: {missing_fields}"
                )

            if env_file := config.get("env"):
                env_path = os.path.abspath(os.path.normpath(env_file))
                if os.path.exists(env_path):
                    if not load_dotenv(env_path):
                        # log warning only if dotenv is not empty
                        if os.path.getsize(env_path) > 0:
                            logger.warning(
                                f"Could not load environment variables from {env_path}"
                            )
                    else:
                        logger.debug(f"Loaded environment variables from {env_path}")

            self._config = config
            self._load_workflows()
            return config
        except Exception as e:
            logger.error(f"Failed to load llama_index.json: {str(e)}")
            raise

    def _load_workflows(self):
        """Load all workflow configurations"""
        if not self._config:
            return

        self._workflows = [
            WorkflowConfig.from_config(name, path)
            for name, path in self._config["workflows"].items()
        ]

    @property
    def workflows(self) -> List[WorkflowConfig]:
        """Get all workflow configurations"""
        if not self._workflows:
            self.load_config()
        return self._workflows

    def get_workflow(self, name: str) -> Optional[WorkflowConfig]:
        """Get a specific workflow configuration by name"""
        return next((w for w in self.workflows if w.name == name), None)

    @property
    def dependencies(self) -> List[str]:
        """Get project dependencies"""
        return self._config.get("dependencies", []) if self._config else []

    @property
    def env_file(self) -> Optional[str]:
        """Get environment file path"""
        return self._config.get("env") if self._config else None
