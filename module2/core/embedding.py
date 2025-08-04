import os

import torch
from pymongo import UpdateOne, MongoClient
from transformers import AutoTokenizer, AutoModel

from module2.classes.Filing import Filing


def insert_filing_with_embeddings(filing: Filing, chunks:list[str], embeddings: torch.Tensor):

    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("DB_NAME")]
    collection = db[os.getenv("COLLECTION_NAME")]
    filings  = []
    bulk_ops = []
    for i, chunk in enumerate(chunks):
        # Create a new Filing object for each chunk
        chunk_filing = Filing(
            cik=filing.cik,
            ticker=filing.ticker,
            filing_type=filing.filing_type,
            year=filing.year,
            text_chunk=chunk,
            source=filing.source,
            embedding=embeddings[i].numpy().tolist()  # Convert tensor to list for MongoDB
        )
        # Insert the chunk filing into the collection
        filings.append(chunk_filing.to_json())
        bulk_ops.append(UpdateOne(
            {"cik": chunk_filing.cik, "ticker": chunk_filing.ticker, "filing_type": chunk_filing.filing_type, "year": chunk_filing.year, "text_chunk": chunk_filing.text_chunk},
            {"$setOnInsert": chunk_filing.to_json()},
            upsert=True
        ))

    result = collection.bulk_write(bulk_ops)
    return result

def calculate_embeddings_from_chunks(model, tokenizer, chunks: list[str]):
    model.eval()

    # Tokenize sentences
    encoded_input = tokenizer(chunks, padding=True, truncation=True, return_tensors='pt')
    # for s2p(short query to long passage) retrieval task, add an instruction to query (not add instruction for passages)
    # encoded_input = tokenizer([instruction + q for q in queries], padding=True, truncation=True, return_tensors='pt')

    # Compute token embeddings
    with torch.no_grad():
        model_output = model(**encoded_input)
        # Perform pooling. In this case, cls pooling.
        chunk_embeddings = model_output[0][:, 0]
    # normalize embeddings
    embeddings = torch.nn.functional.normalize(chunk_embeddings, p=2, dim=1)
    return embeddings

def calculate_and_insert_embeddings(filing: Filing, model, tokenizer, chunks: list[str]):
    embeddings = calculate_embeddings_from_chunks(model, tokenizer, chunks)
    result = insert_filing_with_embeddings(filing, chunks, embeddings)
    print(f"Inserted IDs: {result.upserted_ids}")
    print(f"Skipped dupllicates: {result.matched_count}")
    print(f"Failed Inserts: {len(result.bulk_api_result.get('writeErrors', []))}")

if __name__ == "__main__":
    # Example usage
    cik = "0000320193"
    ticker = "AAPL"
    filing_type = "10-K"
    year = "2023"

    source = "https://www.sec.gov/Archives/edgar/data/320193/000032019323000012/aapl-20230930.htm"
    filing = Filing(cik, ticker, filing_type, year, source)

    chunks = ["This is a sample chunk of text from the filing", "This is another chunk of text from the filing.", "This is yet another chunk of text from the filing."]
    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-small-en')
    model = AutoModel.from_pretrained('BAAI/bge-small-en')


    calculate_and_insert_embeddings(filing, model, tokenizer, chunks)