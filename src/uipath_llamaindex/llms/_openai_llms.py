import os
from enum import Enum
from typing import Any, Union

from llama_index.llms.azure_openai import AzureOpenAI


class ModelName(Enum):
    GPT_4_1_2025_04_14 = "gpt-4.1-2025-04-14"
    GPT_4_1_MINI_2025_04_14 = "gpt-4.1-mini-2025-04-14"
    GPT_4_1_NANO_2025_04_14 = "gpt-4.1-nano-2025-04-14"
    GPT_4O_2024_05_13 = "gpt-4o-2024-05-13"
    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"
    GPT_4O_2024_11_20 = "gpt-4o-2024-11-20"
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"
    O3_MINI_2025_01_31 = "o3-mini-2025-01-31"
    TEXT_DAVINCI_003 = "text-davinci-003"


# Define your custom AzureOpenAI class with default settings
class UiPathOpenAI(AzureOpenAI):
    def __init__(
        self,
        model: Union[str, ModelName] = ModelName.GPT_4O_MINI_2024_07_18,
        api_version: str = "2024-10-21",
        **kwargs: Any,
    ):
        default_headers_dict = {
            "X-UIPATH-STREAMING-ENABLED": "false",
            "X-UiPath-LlmGateway-RequestingProduct": "uipath-python-sdk",
            "X-UiPath-LlmGateway-RequestingFeature": "llama-index-agent",
        }
        model_value = model.value if isinstance(model, ModelName) else model

        base_url = os.environ.get(
            "UIPATH_URL", "https://cloud.uipath.com/account/tenant"
        ).rstrip("/")

        defaults = {
            "model": model_value,
            "deployment_name": model_value,
            "azure_endpoint": f"{base_url}/llmgateway_/",
            "api_key": os.environ.get("UIPATH_ACCESS_TOKEN"),
            "api_version": api_version,
            "is_chat_model": True,
            "default_headers": default_headers_dict,
        }
        final_kwargs = {**defaults, **kwargs}
        super().__init__(**final_kwargs)