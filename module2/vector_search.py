import os
from dotenv import load_dotenv
from pymongo import MongoClient
from transformers import AutoTokenizer, AutoModel

from module2.core.search_service import vector_search_with_filter

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = "embedded_chunks" 
SEARCH_INDEX_NAME = os.getenv("SEARCH_INDEX_NAME") # this index should be created for the above collection
MODEL_NAME = 'BAAI/bge-small-en'

if not all([MONGO_URI, DB_NAME, COLLECTION_NAME, SEARCH_INDEX_NAME]):
    raise ValueError("please ensure that all necessary environment variables are set")

def get_mongo_collection():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print(f"Successfully connected to the collection:{db.name}.{collection.name}")
        return collection
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return None

def get_embedding_model():
    print(f"loading model: {MODEL_NAME}...")
    model = AutoModel.from_pretrained(MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model.eval()
    return model, tokenizer

def print_results(results: list):
    print("\n--- search results ---")
    if not results:
        print("No relevant results found")
    else:
        print(f"Found {len(results)} results:")
        for doc in results:
            print(f"\n Similarity score: {doc['score']:.4f}")
            print(f"Source: {doc.get('ticker', 'N/A')} ({doc.get('year', 'N/A')}) - CIK: {doc.get('cik', 'N/A')}")
            print(f"Match text: {doc.get('text_chunk', 'no text')}")
            print("-" * 20)

if __name__ == "__main__":
    collection = get_mongo_collection()
    if collection is None: exit()
    
    model, tokenizer = get_embedding_model()

    # define query
    user_query = "What are the risks related to competition?"
    # user_query = "What was the value for Receivable net Accounts  for the end date 2022-09-24?"

    print(f"\n user query: '{user_query}'")

    # vector search

    #  Unfiltered search
    print("\n--- search 1:  Unfiltered search ---")
    unfiltered_results = vector_search_with_filter(
        collection=collection,
        index_name=SEARCH_INDEX_NAME,
        query_text=user_query,
        model=model,
        tokenizer=tokenizer,
        limit=3
    )
    print_results(unfiltered_results)
    
    # search with metadata filtering
    print("\n--- search 2: search with ticker='AAPL' metadata filtering ---")
    ticker_filter = {
        "ticker": { "$eq": "AAPL" }
    }
    filtered_results_ticker = vector_search_with_filter(
        collection=collection,
        index_name=SEARCH_INDEX_NAME,
        query_text=user_query,
        model=model,
        tokenizer=tokenizer,
        limit=3,
        filters=ticker_filter
    )
    print_results(filtered_results_ticker)


    print("\n--- search 3: search with year >= 2023 metadata filtering ---")
    year_filter = {
        "year": { "$gte": 2023 }
    }
    filtered_results_year = vector_search_with_filter(
        collection=collection,
        index_name=SEARCH_INDEX_NAME,
        query_text=user_query,
        model=model,
        tokenizer=tokenizer,
        limit=3,
        filters=year_filter 
    )
    print_results(filtered_results_year)