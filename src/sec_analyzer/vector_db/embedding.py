from __future__ import annotations
import os
from typing import List, Optional

import torch
from pymongo import UpdateOne, MongoClient

from sec_analyzer.schemas import Filing
from sec_analyzer.utils import hash_text

EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))


def _get_collection():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("DB_NAME")]
    return db[os.getenv("COLLECTION_NAME", "embedded_chunks")]


def calculate_embeddings_from_chunks(model, tokenizer, chunks: List[str]) -> torch.Tensor:
    encoded_input = tokenizer(chunks, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
        cls_embeddings = model_output[0][:, 0]
    embeddings = torch.nn.functional.normalize(cls_embeddings, p=2, dim=1)
    return embeddings


def insert_filing_with_embeddings(
    filing: Filing,
    chunks: List[str],
    embeddings: torch.Tensor,
    collection_name: Optional[str] = None,
):
    assert embeddings.shape[0] == len(chunks), "embeddings and chunks size mismatch"
    assert embeddings.shape[1] == EMBED_DIM, f"Embedding dim {embeddings.shape[1]} != expected {EMBED_DIM}"

    collection = _get_collection() if collection_name is None else MongoClient(os.getenv("MONGODB_URI"))[os.getenv("DB_NAME")][collection_name]

    bulk_ops = []
    for i, chunk in enumerate(chunks):
        doc = Filing(
            cik=filing.cik,
            ticker=filing.ticker,
            filing_type=filing.filing_type,
            year=filing.year,
            source=filing.source,
            text_chunk=chunk,
            embedding=embeddings[i].cpu().numpy().tolist(),
        ).to_mongo()
        # Deduplicate on content hash
        content_hash = hash_text(doc["text_chunk"]) if doc.get("text_chunk") else None
        filter_q = {"content_hash": content_hash} if content_hash else {"text_chunk": doc["text_chunk"]}
        doc["content_hash"] = content_hash

        bulk_ops.append(UpdateOne(filter_q, {"$setOnInsert": doc}, upsert=True))

    if not bulk_ops:
        return None
    return collection.bulk_write(bulk_ops)