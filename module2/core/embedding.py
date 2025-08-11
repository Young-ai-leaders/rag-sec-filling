import os

import torch
from pymongo import UpdateOne, MongoClient
from transformers import AutoTokenizer, AutoModel

from module2.classes.Filing import Filing


def insert_filing_with_embeddings(filing: Filing, chunks: list[str], embeddings: torch.Tensor, collection_name: str):
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("DB_NAME")]
    # use the passed-in collection_name
    collection = db[collection_name] 
    
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
            embedding=embeddings[i].numpy().tolist() # Convert tensor to list for MongoDB
        )
        bulk_ops.append(UpdateOne(
            {"text_chunk": chunk_filing.text_chunk}, # use text_chunk as the unique identifier
            {"$setOnInsert": chunk_filing.to_json()},
            upsert=True
        ))

    if not bulk_ops:
        print("No writable operations.")
        return None
        
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

def calculate_and_insert_embeddings(filing: Filing, model, tokenizer, chunks: list[str], collection_name: str):
    print(f"\n--- processing data for collection '{collection_name}'---")
    embeddings = calculate_embeddings_from_chunks(model, tokenizer, chunks)
    result = insert_filing_with_embeddings(filing, chunks, embeddings, collection_name)
    
    if result:
        print(f"Insert into ‘{collection_name}’ completed")
        print(f"  new documents added: {result.upserted_count}")
        print(f"  Skip duplicate: {result.matched_count}")
        print(f"  failed writes: {len(result.bulk_api_result.get('writeErrors', []))}")
    else:
        print(f"No data was written to the collection ‘{collection_name}’.")

if __name__ == "__main__":
    # Example usage
    cik = "0000320193"
    ticker = "AAPL"
    filing_type = "10-K"
    year = 2023

    source = "https://www.sec.gov/Archives/edgar/data/320193/000032019323000012/aapl-20230930.htm"
    filing = Filing(cik, ticker, filing_type, year, source)

    chunks = ["This is a sample chunk of text from the filing", "This is another chunk of text from the filing.", "This is yet another chunk of text from the filing."]
    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-small-en')
    model = AutoModel.from_pretrained('BAAI/bge-small-en')


    calculate_and_insert_embeddings(filing, model, tokenizer, chunks)