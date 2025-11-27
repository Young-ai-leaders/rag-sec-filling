from typing import Any, Optional, Dict, List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pymongo.collection import Collection

from src.sec_analyzer.vector_db.search_service import vector_search_with_filter


class SECRetriever(BaseRetriever):
    """LangChain-compatible retriever for SEC filing vector search.

    This retriever wraps the MongoDB Atlas vector search functionality
    and integrates with LangChain's RAG pipeline.
    """
    collection: Collection
    search_index_name: str
    model: Any
    tokenizer: Any
    k: int = 5
    metadata_fields: List[str] = ["cik", "ticker", "year", "source"]

    def _get_relevant_documents(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Return relevant documents for the query.

        Args:
            query: The search query text
            filters: Optional MongoDB filters to apply (e.g., {"ticker": "AAPL"})

        Returns:
            List of LangChain Document objects
        """
        # Perform vector search
        raw_results = vector_search_with_filter(
            collection=self.collection,
            index_name=self.search_index_name,
            query_text=query,
            model=self.model,
            tokenizer=self.tokenizer,
            limit=self.k,
            filters=filters
        )

        # Convert to LangChain Documents
        documents = []
        for result in raw_results:
            # Extract metadata
            metadata = {field: result.get(field) for field in self.metadata_fields}
            metadata["score"] = result.get("score")

            # Create Document
            doc = Document(
                page_content=result.get("text_chunk", ""),
                metadata=metadata
            )
            documents.append(doc)

        return documents