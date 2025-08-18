from __future__ import annotations
from typing import Optional, Dict, Any, List

import torch
from pymongo.collection import Collection


def generate_embedding(text: str, model, tokenizer) -> List[float]:
    encoded_input = tokenizer(text, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
        embedding = model_output[0][:, 0]
    normalized = torch.nn.functional.normalize(embedding, p=2, dim=1)
    return normalized.squeeze().tolist()


def vector_search_with_filter(
    collection: Collection,
    index_name: str,
    query_text: str,
    model,
    tokenizer,
    limit: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> list:
    query_vector = generate_embedding(query_text, model, tokenizer)

    search_stage: Dict[str, Any] = {
        "$vectorSearch": {
            "index": index_name,
            "path": "embedding",
            "queryVector": query_vector,
            "numCandidates": 100,
            "limit": limit,
        }
    }
    if filters:
        search_stage["$vectorSearch"]["filter"] = filters

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
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    return list(collection.aggregate(pipeline))