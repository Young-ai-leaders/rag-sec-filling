from pymongo.collection import Collection
from typing import Optional, Dict, Any

from transformers import AutoTokenizer, AutoModel
import torch

def generate_embedding(text: str, model, tokenizer) -> list[float]:
    encoded_input = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
        embedding = model_output[0][:, 0]
    normalized_embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
    return normalized_embedding.squeeze().tolist()


def vector_search_with_filter(
    collection: Collection,
    index_name: str,
    query_text: str,
    model,
    tokenizer,
    limit: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> list:
    """

    Arguments:
    - collection: the pymongo Collection object to query。
    - index_name: name of Atlas Vector Search index
    - query_text: Natural language queries from users.
    - model, tokenizer: Embedding models and tokenizers used to generate query vectors.
    - limit: number of results returned.
    - filters: An optional dictionary used to define filter conditions
    """
    
    # generate query vectors
    query_vector = generate_embedding(query_text, model, tokenizer)

    # 2. build the $vectorSearch aggregation stage
    search_stage = {
        "$vectorSearch": {
            "index": index_name,
            "path": "embedding",
            "queryVector": query_vector,
            "numCandidates": 100, # typically 10-20 times the limit
            "limit": limit
        }
    }
    
    # add filter to the $vectorSearch stage
    if filters:
        # use the ‘filter’ parameter
        search_stage["$vectorSearch"]["filter"] = filters

    # Build a complete aggregation pipeline
    pipeline = [
        search_stage,
        {
            "$project": {
                "_id": 0,
                "cik": 1,
                "ticker": 1,
                "year": 1,
                "text_chunk": 1,
                "source": 1,
                "score": { "$meta": "vectorSearchScore" }
            }
        }
    ]
    
    # execute the query and return the results.
    try:
        results = list(collection.aggregate(pipeline))
        return results
    except Exception as e:
        print(f"Vector search failed:{e}")
        return []