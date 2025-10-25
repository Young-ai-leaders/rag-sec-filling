from typing import Collection

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import Any

from src.sec_analyzer.vector_db.search_service import vector_search_with_filter


class SECRetriever(BaseRetriever):
    collection: Any
    search_index_name: str
    model: Any
    tokenizer: Any
    k: int = 5


    def _get_relevant_documents(self, query: str, filters=None) -> list[Document]:
        """Return the first k documents from the list of documents"""
        results = vector_search_with_filter(
            collection=self.collection,
            index_name=self.search_index_name,
            query_text=query,
            model=self.model,
            tokenizer=self.tokenizer,
            limit=self.k,
            filters=filters
        )
        return results