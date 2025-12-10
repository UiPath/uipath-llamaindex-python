import os
from typing import Any

from llama_index.llms.azure_openai import AzureOpenAI  # type: ignore
from uipath.utils import EndpointManager

from .supported_models import OpenAIModel


class UiPathOpenAI(AzureOpenAI):
    def __init__(
        self,
        model: str | OpenAIModel = OpenAIModel.GPT_4O_MINI_2024_07_18,
        api_version: str = "2024-10-21",
        **kwargs: Any,
    ):
        default_headers_dict = {
            "X-UIPATH-STREAMING-ENABLED": "false",
            "X-UiPath-LlmGateway-RequestingProduct": "uipath-python-sdk",
            "X-UiPath-LlmGateway-RequestingFeature": "llama-index-agent",
        }
        model_value = model.value if isinstance(model, OpenAIModel) else model

        base_url = os.environ.get("UIPATH_URL", "EMPTY").rstrip("/")

        if base_url == "EMPTY":
            raise ValueError(
                "UIPATH_URL environment variable is not set. Please run uipath auth."
            )

        defaults = {
            "model": model_value,
            "deployment_name": model_value,
            "azure_endpoint": f"{base_url}/{EndpointManager.get_passthrough_endpoint().format(model=model_value, api_version=api_version)}",
            "api_key": os.environ.get("UIPATH_ACCESS_TOKEN"),
            "api_version": api_version,
            "is_chat_model": True,
            "default_headers": default_headers_dict,
        }
        final_kwargs = {**defaults, **kwargs}
        super().__init__(**final_kwargs)
