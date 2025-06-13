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
        uipath_access_token = os.environ.get("UIPATH_ACCESS_TOKEN")
        auth_header_value = (
            "Bearer " + str(uipath_access_token) if uipath_access_token else None
        )
        default_headers_dict = {
            "X-UIPATH-STREAMING-ENABLED": "false",
            "X-UiPath-LlmGateway-RequestingProduct": "uipath-python-sdk",
            "X-UiPath-LlmGateway-RequestingFeature": "llama-index-agent",
        }
        if auth_header_value:
            default_headers_dict["Authorization"] = auth_header_value
        model_value = model.value if isinstance(model, EmbeddingModelName) else model

        base_url = os.environ.get(
            "UIPATH_URL", "https://cloud.uipath.com/account/tenant"
        ).rstrip("/")

        defaults = {
            "model": model_value,
            "deployment_name": model_value,
            "azure_endpoint": f"{base_url}/llmgateway_/",
            "api_key": uipath_access_token,
            "api_version": api_version,
            "default_headers": default_headers_dict,
        }
        final_kwargs = {**defaults, **kwargs}
        super().__init__(**final_kwargs)
