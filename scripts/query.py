from __future__ import annotations
import os, sys, argparse
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.append(os.path.abspath("src"))

from sec_analyzer.vector_db.model_loader import load_model_and_tokenizer
from sec_analyzer.vector_db.search_service import vector_search_with_filter


def main():
    parser = argparse.ArgumentParser(description="Module 2 query: semantic vector search over MongoDB Atlas")
    parser.add_argument("--q", required=True, help="Query text")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--ticker", help="Optional filter: ticker")
    parser.add_argument("--year_gte", type=int, help="Optional filter: year >=")
    parser.add_argument("--model", default=os.getenv("MODEL_NAME", "BAAI/bge-small-en"))
    args = parser.parse_args()

    load_dotenv()

    client = MongoClient(os.getenv("MONGODB_URI"))
    col = client[os.getenv("DB_NAME")][os.getenv("COLLECTION_NAME", "embedded_chunks")]
    index_name = os.getenv("SEARCH_INDEX_NAME", "vector_index")

    model, tokenizer = load_model_and_tokenizer(args.model)

    filters = {}
    if args.ticker:
        filters["ticker"] = {"$eq": args.ticker}
    if args.year_gte is not None:
        filters["year"] = {"$gte": args.year_gte}
    if not filters:
        filters = None

    results = vector_search_with_filter(
        collection=col,
        index_name=index_name,
        query_text=args.q,
        model=model,
        tokenizer=tokenizer,
        limit=args.k,
        filters=filters,
    )

    if not results:
        print("No relevant results found.")
        return

    print(f"Found {len(results)} result(s):")
    for i, doc in enumerate(results, 1):
        print(f"\n[{i}] score={doc['score']:.4f} | {doc.get('ticker','?')} ({doc.get('year','?')})")
        print(doc.get("text_chunk", "<no text>"))
        print("-" * 60)


if __name__ == "__main__":
    main()