# cli.py
import os
import sys
import click
from pathlib import Path
from dotenv import load_dotenv

# Ensure the 'src' directory is on the Python path to find the 'sec_analyzer' package.
sys.path.append(os.path.abspath("src"))
load_dotenv()

# --- Imports from our sec_analyzer package ---
from sec_analyzer import FilingsFetcher, FilingsExtractor, FilingParser
from sec_analyzer.config import DEFAULT_FILINGS_DIRECTORY, DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY
from sec_analyzer.vector_db.model_loader import load_model_and_tokenizer
from sec_analyzer.vector_db.chunking import (
    process_csv_to_natural_language,
    process_csv_to_raw_string,
    process_csv_original_method,
)
from sec_analyzer.schemas import Filing
from sec_analyzer.vector_db.embedding import insert_filing_with_embeddings
from sec_analyzer.vector_db.search_service import vector_search_with_filter
from pymongo import MongoClient


@click.group(help="A command-line tool to fetch, process, and query SEC filings.")
def cli():
    """Main entry point for the SEC Analyzer CLI."""
    pass


@cli.command()
@click.option("--ticker", help="Company ticker symbol (e.g., AAPL)")
@click.option("--cik", help="Company CIK number (e.g., 0000320193)")
@click.option("--years", multiple=True, type=int, help="Years to fetch (e.g., --years 2023 --years 2022)")
@click.option("--num-filings", default=4, type=int, show_default=True, help="Number of recent filings to get per year.")
def fetch(ticker, cik, years, num_filings):
    """Fetch SEC 10-K filings and save them locally."""
    if not ticker and not cik:
        raise click.UsageError("Error: Must provide either --ticker or --cik.")
    
    fetcher = FilingsFetcher()
    effective_cik = cik or fetcher.get_cik_from_ticker(ticker)
    if not effective_cik:
        click.echo(f"Could not determine CIK for ticker '{ticker}'. Aborting.", err=True)
        return
        
    click.echo(f"Starting to fetch filings for {ticker or 'CIK:'} ({effective_cik})...")
    fetcher.get_filings(cik=effective_cik, ticker=ticker, years=list(years), num_filings=num_filings)
    click.echo("✅ Fetch complete.")

@cli.command()
@click.option("--ticker", required=True, help="Ticker symbol to process.")
def extract(ticker):
    """Extract structured XBRL data from downloaded filings into CSV files."""
    try:
        extractor = FilingsExtractor()
        click.echo(f"Finding downloaded filings for {ticker}...")
        filing_list = extractor.get_company_filings(ticker)
        
        if not filing_list:
            click.echo(f"No filings found for {ticker}. Run the 'fetch' command first.", err=True)
            return
            
        click.echo(f"Found {len(filing_list)} filings. Extracting data...")
        extracted_data = extractor.extract_data(ticker, filing_list)
        extractor.save_to_csv(ticker, extracted_data)
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}. Ensure filings for '{ticker}' have been downloaded.", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

@cli.command()
@click.option("--ticker", required=True, help="Ticker symbol to process.")
def parse(ticker):
    """Parse textual 'Item 8' data from downloaded filings into a single JSON file."""
    try:
        parser = FilingParser()
        filings_path = Path(DEFAULT_FILINGS_DIRECTORY) / ticker
        output_file = Path(DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY) / f"parsed_{ticker}.json"

        click.echo(f"Parsing text from filings in: {filings_path}")
        parser.parse_all_filings_structured(filings_path, output_file)

    except FileNotFoundError as e:
        click.echo(f"Error: {e}. Ensure filings for '{ticker}' have been downloaded.", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)


@cli.command()
@click.option("--ticker", required=True, help="Ticker symbol to process.")
def parse_risk_factors(ticker):
    """Parse 'Item 1A: Risk Factors' from downloaded filings into a JSON file."""
    try:
        parser = FilingParser()
        filings_path = Path(DEFAULT_FILINGS_DIRECTORY) / ticker
        output_file = Path(DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY) / f"risk_factors_{ticker}.json"

        click.echo(f"Parsing risk factors from filings in: {filings_path}")
        parser.parse_risk_factors_all_filings(filings_path, output_file)

    except FileNotFoundError as e:
        click.echo(f"Error: {e}. Ensure filings for '{ticker}' have been downloaded.", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)

@cli.command()
@click.option("--csv", "csv_path", required=True, help="Path to the extracted CSV file to ingest.")
@click.option("--ticker", required=True)
@click.option("--cik", required=True)
@click.option("--year", type=int, required=True)
@click.option("--filing-type", default="10-K-XBRL", show_default=True)
@click.option("--source", default="", help="Source document name. Defaults to CSV filename.")
@click.option("--mode", type=click.Choice(["nl", "raw", "merge"]), default="nl", show_default=True)
@click.option("--model", default=os.getenv("MODEL_NAME", "BAAI/bge-small-en"), show_default=True)
def ingest(csv_path, ticker, cik, year, filing_type, source, mode, model):
    """Ingest a CSV file into the vector database."""
    if mode == "nl":
        chunks = process_csv_to_natural_language(csv_path)
    elif mode == "raw":
        chunks = process_csv_to_raw_string(csv_path)
    else:
        chunks = process_csv_original_method(csv_path)
    
    if not chunks:
        raise click.ClickException("No chunks produced from CSV.")

    mdl, tok = load_model_and_tokenizer(model)
    
    from sec_analyzer.vector_db.embedding import calculate_embeddings_from_chunks
    embs = calculate_embeddings_from_chunks(mdl, tok, chunks)
    
    filing = Filing(cik=cik, ticker=ticker, filing_type=filing_type, year=year, source=source or os.path.basename(csv_path))
    result = insert_filing_with_embeddings(filing, chunks, embs)
    
    upserts = result.upserted_count if result else 0
    matched = result.matched_count if result else 0
    click.echo(f"✅ Ingest complete. Upserts: {upserts} | Matched: {matched}")

@cli.command()
@click.option("--q", "query_text", required=True, help="The question you want to ask.")
@click.option("--k", type=int, default=5, show_default=True, help="Number of results to return.")
@click.option("--ticker", help="Filter results by a specific ticker.")
@click.option("--year-gte", type=int, help="Filter results to years greater than or equal to this value.")
@click.option("--model", default=os.getenv("MODEL_NAME", "BAAI/bge-small-en"), show_default=True)
def query(query_text, k, ticker, year_gte, model):
    """Perform a semantic search on the vector database."""
    client = MongoClient(os.getenv("MONGODB_URI"))
    col = client[os.getenv("DB_NAME")][os.getenv("COLLECTION_NAME", "embedded_chunks")]
    index_name = os.getenv("SEARCH_INDEX_NAME", "vector_index")
    mdl, tok = load_model_and_tokenizer(model)

    filters = {}
    if ticker:
        filters["ticker"] = {"$eq": ticker}
    if year_gte is not None:
        filters["year"] = {"$gte": year_gte}
    
    # Pass None if filters is empty, not the empty dict itself.
    final_filters = filters if filters else None

    results = vector_search_with_filter(
        collection=col, 
        index_name=index_name, 
        query_text=query_text, 
        model=mdl, 
        tokenizer=tok, 
        limit=k, 
        filters=final_filters
    )
    
    if not results:
        click.echo("No relevant results found.")
        return

    click.echo(f"Found {len(results)} result(s):")
    for i, doc in enumerate(results, 1):
        click.echo(f"\n[{i}] score={doc['score']:.4f} | {doc.get('ticker','?')} ({doc.get('year','?')})")
        click.echo(doc.get("text_chunk", "<no text>"))
        click.echo("-" * 60)

if __name__ == "__main__":
    cli()