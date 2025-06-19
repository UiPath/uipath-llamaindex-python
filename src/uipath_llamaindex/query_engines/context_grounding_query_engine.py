from typing import Optional

from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.response_synthesizers import BaseSynthesizer
from uipath import UiPath

from uipath_llamaindex.retrievers import ContextGroundingRetriever


class ContextGroundingQueryEngine(CustomQueryEngine):
    """RAG Query Engine."""

    def __init__(
        self,
        response_synthesizer: BaseSynthesizer,
        index_name: str,
        folder_path: Optional[str] = None,
        folder_key: Optional[str] = None,
        uipath: Optional[UiPath] = None,
        number_of_results: Optional[int] = 10,
        **kwargs,
    ):
        super().__init__()
        self._retriever = ContextGroundingRetriever(
            index_name=index_name,
            folder_path=folder_path,
            folder_key=folder_key,
            number_of_results=number_of_results,
            uipath=uipath,
            **kwargs,
        )
        self._response_synthesizer = response_synthesizer

    def custom_query(self, query_str: str):
        nodes = self._retriever.retrieve(query_str)
        response_obj = self._response_synthesizer.synthesize(query_str, nodes)
        return response_obj

    async def acustom_query(self, query_str: str):
        nodes = await self._retriever.aretrieve(query_str)
        response_obj = self._response_synthesizer.synthesize(query_str, nodes)
        return response_obj
