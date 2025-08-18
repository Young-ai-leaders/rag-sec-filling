from __future__ import annotations
import os, sys, argparse
from dotenv import load_dotenv

# so we can import from src/
sys.path.append(os.path.abspath("src"))

from sec_analyzer.schemas import Filing
from sec_analyzer.vector_db.chunking import (
    process_csv_to_natural_language,
    process_csv_to_raw_string,
    process_csv_original_method,
)
from sec_analyzer.vector_db.embedding import calculate_embeddings_from_chunks, insert_filing_with_embeddings
from sec_analyzer.vector_db.model_loader import load_model_and_tokenizer


def main():
    parser = argparse.ArgumentParser(description="Module 2 ingestion: CSV → chunks → embeddings → MongoDB")
    parser.add_argument("--csv", required=True, help="Path to CSV (XBRL facts export)")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--cik", required=True)
    parser.add_argument("--filing_type", default="10-K-XBRL")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--source", default="")
    parser.add_argument("--mode", choices=["nl", "raw", "merge"], default="nl",
                        help="Chunking mode: nl=natural language, raw=row strings, merge=merge-all-then-split")
    parser.add_argument("--model", default=os.getenv("MODEL_NAME", "BAAI/bge-small-en"))
    args = parser.parse_args()

    load_dotenv()

    # choose chunking strategy
    if args.mode == "nl":
        chunks = process_csv_to_natural_language(args.csv)
    elif args.mode == "raw":
        chunks = process_csv_to_raw_string(args.csv)
    else:
        chunks = process_csv_original_method(args.csv)

    if not chunks:
        print("No chunks produced; aborting.")
        return

    model, tokenizer = load_model_and_tokenizer(args.model)

    embeddings = calculate_embeddings_from_chunks(model, tokenizer, chunks)

    filing = Filing(
        cik=args.cik,
        ticker=args.ticker,
        filing_type=args.filing_type,
        year=args.year,
        source=args.source or os.path.basename(args.csv),
    )

    result = insert_filing_with_embeddings(filing, chunks, embeddings)
    if result:
        print("Upserts:", result.upserted_count, "Matched (dupes):", result.matched_count)
        print("WriteErrors:", len(result.bulk_api_result.get("writeErrors", [])))
    else:
        print("Nothing written.")


if __name__ == "__main__":
    main()