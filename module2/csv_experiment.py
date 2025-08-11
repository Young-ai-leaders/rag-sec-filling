
import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModel

from module2.classes.Filing import Filing
from module2.core.chunking import process_csv_to_natural_language, process_csv_to_raw_string, process_csv_original_method, get_text_from_parsed_json, chunk_unstructured_text
from module2.core.embedding import calculate_and_insert_embeddings




load_dotenv()

def different_csv_and_json_chunk():
    # define general information
    CIK = "0000320193"
    TICKER = "AAPL"
    FILING_TYPE = "10-K-XBRL"
    YEAR = 2023
    SOURCE_URL = "0000320193-23-000106.csv"
    CSV_FILE_PATH = "output/AAPL/0000320193-23-000106.csv"
    PARSED_JSON_PATH = "output/parsed_AAPL.json"

    COLLECTION_NL = "chunks_natural_language"
    COLLECTION_RAW = "chunks_raw_string"
    COLLECTION_ORIGINAL = "chunks_original_method"
    
    # Loading Embedding model
    print("\n Loading Embedding model")
    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-small-en')
    model = AutoModel.from_pretrained('BAAI/bge-small-en')
    print("Model loaded successfully")

    #  Create a basic filing object 
    base_filing = Filing(cik=CIK, ticker=TICKER, filing_type=FILING_TYPE, year=YEAR, source=SOURCE_URL)

    # natural_language chunks
    print("\n processing natural_language")
    chunks_nl = process_csv_to_natural_language(CSV_FILE_PATH)
    if chunks_nl:
        calculate_and_insert_embeddings(filing=base_filing, model=model, tokenizer=tokenizer, chunks=chunks_nl, collection_name=COLLECTION_NL)

    # raw string chunks, One chunk per line
    print("\n processing raw string")
    chunks_raw = process_csv_to_raw_string(CSV_FILE_PATH)
    if chunks_raw:
        calculate_and_insert_embeddings(filing=base_filing, model=model, tokenizer=tokenizer, chunks=chunks_raw, collection_name=COLLECTION_RAW)

    # merge the entire CSV file into one string, then perform split
    print("\n processing one string")
    chunks_original = process_csv_original_method(CSV_FILE_PATH)
    if chunks_original:
        calculate_and_insert_embeddings(filing=base_filing, model=model, tokenizer=tokenizer, chunks=chunks_original, collection_name=COLLECTION_ORIGINAL)

    print(f"MongoDB COLLECTION: '{COLLECTION_NL}', '{COLLECTION_RAW}', 和 '{COLLECTION_ORIGINAL}'")

"""
    print("--- json chunking ---")
    print(f"company: {TICKER}, file type: {FILING_TYPE}, year: {YEAR}")

    # extract all text from JSON files
    print(f"\nextracting text from {PARSED_JSON_PATH}")
    full_text_from_filing = get_text_from_parsed_json(PARSED_JSON_PATH)

    # Splitting long text
    print(f"\n Splitting the extracted long text into chunks")
    chunks = chunk_unstructured_text(full_text_from_filing, chunk_size=512, overlap=50)

    # Loading Embedding model
    print("\n Loading Embedding model")
    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-small-en')
    model = AutoModel.from_pretrained('BAAI/bge-small-en')
    print("Model loaded successfully")

    # create  base filing object
    base_filing = Filing(cik=CIK, ticker=TICKER, filing_type=FILING_TYPE, year=YEAR, source=SOURCE_URL)

    # calculate_and_insert_embeddings
    calculate_and_insert_embeddings(filing=base_filing, model=model, tokenizer=tokenizer, chunks=chunks)
"""

if __name__ == "__main__":
    different_csv_and_json_chunk()