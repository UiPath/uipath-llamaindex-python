from typing import List, Optional

from llama_index.core.retrievers import (
    BaseRetriever,
)
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from uipath import UiPath
from uipath.models import ContextGroundingQueryResponse


class ContextGroundingRetriever(BaseRetriever):
    def __init__(
        self,
        index_name: str,
        folder_path: Optional[str] = None,
        folder_key: Optional[str] = None,
        uipath: Optional[UiPath] = None,
        number_of_results: Optional[int] = 10,
        **kwargs,
    ):
        super().__init__()
        self._index_name = index_name
        self._folder_path = folder_path
        self._folder_key = folder_key
        self._uipath = uipath or UiPath()
        self._number_of_results = number_of_results
        self._results: list[ContextGroundingQueryResponse] = []

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        self._results = self._uipath.context_grounding.search(
            self._index_name,
            query_bundle.query_str,
            self._number_of_results,
            folder_path=self._folder_path,
            folder_key=self._folder_key,
        )

        return self._to_nodes_with_scores()

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        self._results = await self._uipath.context_grounding.search_async(
            self._index_name,
            query_bundle.query_str,
            self._number_of_results,
            folder_path=self._folder_path,
            folder_key=self._folder_key,
        )

        return self._to_nodes_with_scores()

    def _to_nodes_with_scores(self) -> List[NodeWithScore]:
        nodes_with_scores = []
        for chunk in self._results:
            node = TextNode(
                text=chunk.content,
                metadata={
                    "source_document_id": chunk.source_document_id,
                    "source": chunk.source,
                    "page_number": chunk.page_number,
                },
            )
            nodes_with_scores.append(NodeWithScore(node=node, score=chunk.score))
        return nodes_with_scores
