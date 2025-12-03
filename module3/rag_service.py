
"""RAG Service for SEC Filing Analysis.

Provides a complete RAG pipeline combining SEC filing vector search with LLMs.
"""

import os
import sys
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from module3.cli import run_interactive_cli

sys.path.append(os.path.abspath("src"))

from pymongo import MongoClient
from module3.SECRetriever import SECRetriever
from src.sec_analyzer.vector_db.model_loader import load_model_and_tokenizer

load_dotenv()


class SimpleTextLLM:
    """Simple text-based LLM fallback that returns retrieved context."""

    def invoke(self, input_text):
        """Return a simple text response based on the input."""
        return f"[Simple Text Response] Retrieved context for: {input_text}"

@dataclass
class RAGConfig:
    """Configuration for SEC RAG Service."""
    mongo_uri: str = os.getenv("MONGODB_URI")
    db_name: str = os.getenv("DB_NAME", "sec_filling")
    collection_name: str = os.getenv("COLLECTION_NAME", "embedded_chunks")
    search_index_name: str = os.getenv("SEARCH_INDEX_NAME", "vector_index")
    embedding_model_name: str = os.getenv("MODEL_NAME", "BAAI/bge-small-en")
    llm_model_name: str = "mistral-small-2503"
    llm_temperature: float = 0.0
    retrieval_k: int = 5


class SECRAGService:
    """RAG service for SEC filing analysis with vector search and LLM integration."""

    def __init__(self, **kwargs):
        self.config = RAGConfig(**kwargs)
        if not self.config.mongo_uri:
            raise ValueError("MongoDB URI required (set MONGODB_URI or pass mongo_uri)")

        # Component placeholders
        self.client = self.db = self.collection = None
        self.embedding_model = self.tokenizer = self.retriever = None
        self.rag_chain = self.llm = None

    def setup(self) -> None:
        """Setup all RAG service components."""
        print(f"Loading embedding model: {self.config.embedding_model_name}")
        self.embedding_model, self.tokenizer = load_model_and_tokenizer(self.config.embedding_model_name)

        print(f"Connecting to MongoDB: {self.config.db_name}.{self.config.collection_name}")
        self.client = MongoClient(self.config.mongo_uri)
        self.db = self.client[self.config.db_name]
        self.collection = self.db[self.config.collection_name]

        self.retriever = SECRetriever(
            collection=self.collection,
            search_index_name=self.config.search_index_name,
            model=self.embedding_model,
            tokenizer=self.tokenizer,
            k=self.config.retrieval_k,
        )

        print(f"Initializing LLM: {self.config.llm_model_name}")
        self.llm = self._initialize_llm()

        self.rag_chain = self._build_rag_chain()
        print("SEC RAG Service setup complete!\n")

    def _initialize_llm(self):
        """Initialize LLM with fallback options."""
        # Try MistralAI first
        try:
            from langchain_mistralai.chat_models import ChatMistralAI
            llm = ChatMistralAI(
                model_name=self.config.llm_model_name,
                temperature=self.config.llm_temperature
            )
            print("[SUCCESS] Using MistralAI LLM")
            return llm
        except Exception as e:
            print(f"[WARNING] MistralAI failed: {e}")

        # Try OpenAI as fallback
        try:
            from langchain_openai import ChatOpenAI
            if os.getenv("OPENAI_API_KEY"):
                llm = ChatOpenAI(
                    model_name="gpt-3.5-turbo",
                    temperature=self.config.llm_temperature
                )
                print("[SUCCESS] Using OpenAI LLM (fallback)")
                return llm
        except Exception as e:
            print(f"[WARNING] OpenAI fallback failed: {e}")

        # Final fallback: use a simple text-based response
        print("[WARNING] No LLM available, using simple text response")
        return SimpleTextLLM()

    def _format_context_with_metadata(self, docs: list[Document]) -> str:
        """Format context documents to include both content and metadata.

        Args:
            docs: List of retrieved documents

        Returns:
            Formatted context string with metadata
        """
        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            # Extract metadata
            metadata = doc.metadata
            ticker = metadata.get('ticker', 'N/A')
            year = metadata.get('year', 'N/A')
            source = metadata.get('source', 'N/A')
            score = metadata.get('score', 0)

            # Format document with metadata header
            formatted_doc = f"""[Document {i}] (Score: {score:.4f})
Ticker: {ticker} | Year: {year} | Source: {source}
{doc.page_content}"""
            formatted_docs.append(formatted_doc)

        return "\n\n" + "="*80 + "\n\n".join(formatted_docs)

    def _get_context_with_metadata(self, query: str, filters=None, ticker=None, year_gte=None) -> str:
        """Get and format context documents with metadata.

        Args:
            query: Search query
            filters: MongoDB filters
            ticker: Company ticker filter
            year_gte: Year filter

        Returns:
            Formatted context string
        """
        query_filters = self._build_filters(filters, ticker, year_gte)
        docs = self.retriever._get_relevant_documents(query, filters=query_filters)
        return self._format_context_with_metadata(docs)

    def _build_rag_chain(self):
        """Build the LangChain RAG pipeline."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert financial analyst specializing in SEC filing analysis.

Analyze financial data from SEC 10-K filings and provide insightful, data-driven answers.

IMPORTANT:
- Use ONLY the provided context - do not add external information
- Pay close attention to DATES and YEARS in the context (they appear as 'as of YYYY-MM-DD' or in metadata)
- Analyze trends, patterns, and changes over time when multiple data points are provided
- When you see multiple values for the same metric, identify:
  * The most recent value (highest date/year)
  * Trends over time
  * Significant changes or fluctuations
- Be precise with figures, units (USD, shares, etc.), and dates
- If the context doesn't contain information to answer a question, state this clearly
- Provide brief explanations for what the numbers might indicate
- Keep responses concise but informative (3-6 paragraphs max)

Context from SEC filings:
{context}"""),
            ("human", "{question}")
        ])

        return (
            {"context": self._get_context_with_metadata, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def _build_filters(self, filters=None, ticker=None, year_gte=None):
        """Build query filters for MongoDB."""
        query_filters = filters.copy() if filters else {}
        if ticker:
            query_filters["ticker"] = {"$eq": ticker}
        if year_gte:
            query_filters["year"] = {"$gte": year_gte}
        return query_filters

    def _decompose_question(self, question: str) -> list[str]:
        """Decompose complex questions into sub-queries for better retrieval.

        Args:
            question: The original question

        Returns:
            List of sub-queries
        """
        # Check if question asks for multiple types of information
        if " and " in question.lower() or " what are " in question.lower():
            # Extract key financial terms
            financial_terms = [
                "stockholders equity", "stockholder equity", "shareholder equity",
                "operating income", "operating loss", "operating profit",
                "net income", "net loss", "revenue", "sales",
                "cash flow", "operating cash flow", "free cash flow",
                "assets", "liabilities", "debt", "expenses",
                "r&d", "research and development",
                "gross profit", "gross margin",
                "ebitda", "ebit"
            ]

            # Check which terms appear in the question
            question_lower = question.lower()
            detected_terms = [term for term in financial_terms if term in question_lower]

            if len(detected_terms) > 1:
                # Create sub-queries for each detected term
                sub_queries = []
                ticker_match = None
                company_match = None

                # Extract ticker or company name if present
                import re
                ticker_match = re.search(r'\b[A-Z]{1,5}\b', question)
                company_match = re.search(r'\b(Apple|Microsoft|Amazon|Google|Tesla|Meta)\b', question, re.IGNORECASE)

                for term in detected_terms:
                    if ticker_match:
                        sub_queries.append(f"{ticker_match.group()} {term}")
                    elif company_match:
                        sub_queries.append(f"{company_match.group()} {term}")
                    else:
                        sub_queries.append(term)

                return sub_queries

        # If no decomposition needed, return original question
        return [question]

    def _multi_query_retrieve(self, queries: list[str], filters=None, ticker=None, year_gte=None) -> list[Document]:
        """Retrieve documents using multiple queries and combine results.

        Args:
            queries: List of sub-queries
            filters: MongoDB filters
            ticker: Company ticker filter
            year_gte: Year filter

        Returns:
            Combined and deduplicated list of documents
        """
        query_filters = self._build_filters(filters, ticker, year_gte)
        all_docs = []
        seen_contents = set()  # Track seen content to avoid duplicates

        # Retrieve for each sub-query
        for sub_query in queries:
            docs = self.retriever._get_relevant_documents(sub_query, filters=query_filters)

            # Add non-duplicate documents
            for doc in docs:
                content_hash = hash(doc.page_content)
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    all_docs.append(doc)

        # Sort by score and return top results (up to original k limit)
        all_docs.sort(key=lambda x: x.metadata.get('score', 0), reverse=True)
        return all_docs[:self.config.retrieval_k]

    def ask(self, question: str, filters=None, ticker=None, year_gte=None) -> str:
        """Ask a question and get an answer from the RAG system."""
        if not self.rag_chain:
            raise RuntimeError("RAG service not initialized. Call setup() first.")

        # Display query info
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        if ticker:
            print(f"Filtered by ticker: {ticker}")
        if year_gte:
            print(f"Filtered by year >= {year_gte}")
        print(f"{'='*60}\n")

        # Decompose complex questions
        sub_queries = self._decompose_question(question)
        if len(sub_queries) > 1:
            print(f"Decomposed into {len(sub_queries)} sub-queries:")
            for i, sq in enumerate(sub_queries, 1):
                print(f"  {i}. {sq}")
            print()

        # Apply filters to retriever
        query_filters = self._build_filters(filters, ticker, year_gte)

        # Create a filtered retriever function
        if query_filters:
            def filtered_retriever(query):
                # Use multi-query retrieval if question was decomposed
                if len(sub_queries) > 1:
                    docs = self._multi_query_retrieve(sub_queries, filters=query_filters)
                else:
                    docs = self.retriever._get_relevant_documents(query, filters=query_filters)
                return self._format_context_with_metadata(docs)

            # Build a completely new chain with the filtered retriever
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert financial analyst specializing in SEC filing analysis.

Analyze financial data from SEC 10-K filings and provide insightful, data-driven answers.

IMPORTANT:
- Use ONLY the provided context - do not add external information
- Pay close attention to DATES and YEARS in the context (they appear as 'as of YYYY-MM-DD' or in metadata)
- Analyze trends, patterns, and changes over time when multiple data points are provided
- When you see multiple values for the same metric, identify:
  * The most recent value (highest date/year)
  * Trends over time
  * Significant changes or fluctuations
- Be precise with figures, units (USD, shares, etc.), and dates
- If the context doesn't contain information to answer a question, state this clearly
- Provide brief explanations for what the numbers might indicate
- Keep responses concise but informative (3-6 paragraphs max)

Context from SEC filings:
{context}"""),
                ("human", "{question}")
            ])

            filtered_rag_chain = (
                {"context": filtered_retriever, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
            )
            return self._invoke_with_retry(filtered_rag_chain, question)
        else:
            return self._invoke_with_retry(self.rag_chain, question)

    def _invoke_with_retry(self, chain, question, max_retries=3):
        """Invoke the chain with retry logic for API failures."""
        for attempt in range(max_retries):
            try:
                return chain.invoke(question)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"[WARNING] API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] All retries failed. Last error: {e}")
                    # Return a fallback response with retrieved context including metadata
                    docs = self.get_context(question, filters=self._build_filters(None, None, None))
                    if docs:
                        context_with_metadata = self._format_context_with_metadata(docs[:3])
                        return f"[Fallback Response] Unable to generate LLM response due to API error.\n\nRetrieved context (showing top 3 documents):\n{context_with_metadata}"
                    else:
                        return f"[Fallback Response] Unable to generate LLM response and no context was retrieved."

    def get_context(self, question: str, filters=None, ticker=None, year_gte=None) -> list[Document]:
        """Get retrieved context documents for debugging/inspection."""
        if not self.retriever:
            raise RuntimeError("RAG service not initialized. Call setup() first.")
        return self.retriever._get_relevant_documents(question, self._build_filters(filters, ticker, year_gte))

    def close(self) -> None:
        """Clean up resources."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")

def main():
    """Main entry point."""
    print("--- SEC Filing Analysis System ---")
    print("Initializing RAG Service components... (this may take a moment)")

    rag_service = SECRAGService(retrieval_k=5)

    try:
        rag_service.setup()
    except Exception as e:
        print(f"\n[FATAL ERROR] Could not initialize service: {e}")
        return

    # Start the CLI loop
    try:
        run_interactive_cli(rag_service)
    finally:
        rag_service.close()
        print("Goodbye!")





if __name__ == "__main__":
    main()


