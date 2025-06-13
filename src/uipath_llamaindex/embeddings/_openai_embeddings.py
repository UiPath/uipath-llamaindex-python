import os
from enum import Enum
from typing import Any, Union

from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding


class EmbeddingModelName(Enum):
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"


class UiPathOpenAIEmbedding(AzureOpenAIEmbedding):
    def __init__(
        self,
        model: Union[
            str, EmbeddingModelName
        ] = EmbeddingModelName.TEXT_EMBEDDING_ADA_002,
        api_version: str = "2024-10-21",
        **kwargs: Any,
    ):
        default_headers_dict = {
            "X-UIPATH-STREAMING-ENABLED": "false",
            "X-UiPath-LlmGateway-RequestingProduct": "uipath-python-sdk",
            "X-UiPath-LlmGateway-RequestingFeature": "llama-index-agent",
        }
        
        model_value = model.value if isinstance(model, EmbeddingModelName) else model

        base_url = os.environ.get(
            "UIPATH_URL", "https://cloud.uipath.com/account/tenant"
        ).rstrip("/")

        defaults = {
            "model": model_value,
            "deployment_name": model_value,
            "azure_endpoint": f"{base_url}/llmgateway_/",
            "api_key": os.environ.get("UIPATH_ACCESS_TOKEN"),
            "api_version": api_version,
            "default_headers": default_headers_dict,
        }
        final_kwargs = {**defaults, **kwargs}
        super().__init__(**final_kwargs)
