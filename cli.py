# cli.py
import click
from pathlib import Path
from typing import List, Optional
from core.fetcher import FilingsFetcher
from core.parser import FilingParser
from core.extractor import FilingsExtractor
from config.settings import (
    DEFAULT_FILINGS_DIRECTORY,
    DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY
)
from utils.helpers import validate_years, sanitize_filename
import requests


@click.group()
@click.version_option(version="0.1", prog_name="SEC Scraper")
def cli():
    """Command-line interface for SEC filings analysis"""
    pass


@cli.command()
@click.option("--ticker", help="Company ticker symbol (e.g. AAPL)", default=None, type=str)
@click.option("--cik", help="SEC Central Index Key (10-digit number)", default=None, type=str)
@click.option("--years", help="Comma-separated years filter (e.g. 2020,2021)", default=None, type=str)
@click.option("--num-filings", default=4, help="Number of filings to fetch", type=int)
def fetch(ticker: Optional[str], cik: Optional[str], years: Optional[str], num_filings: int):
    """Fetch SEC filings for a company"""
    fetcher = FilingsFetcher()

    # Validate input and determine CIK
    if not (ticker or cik):
        raise click.BadParameter("Must provide either --ticker or --cik.")

    actual_cik: str
    company_identifier_for_log: str  # For logging, use ticker if available

    if cik:
        if not cik.isdigit() or not (1 <= len(cik) <= 10):
            raise click.BadParameter("CIK must be 1-10 digits.")
        actual_cik = cik.zfill(10)
        company_identifier_for_log = ticker if ticker else f"CIK:{actual_cik}"
    elif ticker:  # ticker is provided, cik is not
        company_identifier_for_log = ticker
        fetched_cik = fetcher.get_cik_from_ticker(ticker)
        if not fetched_cik:
            # get_cik_from_ticker already prints a message if not found
            raise click.BadParameter(f"Could not find CIK for ticker '{ticker}'.")
        actual_cik = fetched_cik  # Already 10 digits and zfilled
    else:
        # This case should be impossible due to the first check, but as a safeguard:
        raise click.BadParameter("Internal error: CIK could not be determined.")

    # Process years
    year_list_int: Optional[List[int]] = None
    if years:
        raw_year_list = [y.strip() for y in years.split(",") if y.strip()]
        if raw_year_list:  # Only call validate_years if there's something to validate
            year_list_int = validate_years(raw_year_list)
            if year_list_int is None:  # validate_years returns None on fundamental error
                raise click.BadParameter(
                    "Invalid format for years. Please use comma-separated digits (e.g., 2020,2021).")
            if not year_list_int:  # validate_years might return empty list if input was non-digits
                click.echo(
                    f"Warning: No valid years found in filter: '{years}'. Fetching without year constraint based on this filter.")
                year_list_int = None  # Treat as no year filter
        else:  # E.g., --years "" or --years ","
            click.echo("Warning: Years filter was empty. Fetching without year constraint based on this filter.")
            year_list_int = None

    click.echo(
        f"📥 Fetching up to {num_filings} filings for '{company_identifier_for_log}' (Resolved CIK: {actual_cik})...")
    if year_list_int:
        click.echo(f"   Filtering for years: {year_list_int}")

    try:
        # Pass the determined actual_cik, original ticker (for logging/dir naming), and processed year_list_int
        fetcher.get_filings(actual_cik, ticker, year_list_int, num_filings)
        # Success message is now handled within fetcher.get_filings
    except ValueError as e:  # For CIK validation errors from fetcher
        raise click.BadParameter(str(e))
    except requests.exceptions.RequestException as e:
        click.echo(f"❌ A network error occurred during fetch: {e}", err=True)
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred during fetch: {e}", err=True)
        # For deeper debugging, you might want to re-raise or log traceback
        # import traceback
        # click.echo(traceback.format_exc(), err=True)


@cli.command()
@click.argument("ticker")
@click.option("--output", default=None, help="Custom output JSON file path for parsed data")
def parse(ticker: str, output: Optional[str]):
    """Parse financial sections from downloaded filings for a ticker"""
    parser = FilingParser()  # Initializes with DEFAULT_FILINGS_DIRECTORY
    safe_ticker = sanitize_filename(ticker)

    company_filings_path = Path(DEFAULT_FILINGS_DIRECTORY) / safe_ticker

    output_path_obj: Path
    if output:
        output_path_obj = Path(output)
    else:
        output_dir = Path(DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY)
        output_path_obj = output_dir / f"parsed_{safe_ticker}.json"

    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    if not company_filings_path.exists() or not company_filings_path.is_dir():
        raise click.FileError(
            f"No filings directory found for ticker '{ticker}' at '{company_filings_path}'. Please run the 'fetch' command first.")

    click.echo(f"🔍 Parsing filings for '{ticker}' from '{company_filings_path}'...")
    try:
        parser.parse_all_filings_structured(company_filings_path, output_path_obj)
        # Success message is handled by parse_all_filings_structured
    except FileNotFoundError as e:  # Should be caught by the check above, but good practice
        raise click.FileError(str(e))
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred during parsing for '{ticker}': {e}", err=True)
        # import traceback
        # click.echo(traceback.format_exc(), err=True)


@cli.command()
@click.argument("ticker")
@click.option("--output", default=None, help="Custom base output directory for extracted CSVs")
def extract(ticker: str, output: Optional[str]):
    """Extract financial data to CSV for a ticker"""
    extractor = FilingsExtractor()

    # FilingsExtractor.get_company_filings expects the raw ticker and sanitizes it internally
    # to find the directory like ./filings/SAFE_TICKER/
    try:
        filings_to_extract = extractor.get_company_filings(ticker)
    except FileNotFoundError:
        safe_ticker_for_path = sanitize_filename(ticker)
        expected_path = Path(DEFAULT_FILINGS_DIRECTORY) / safe_ticker_for_path
        raise click.FileError(
            f"No filings directory found for ticker '{ticker}' at '{expected_path}'. Please run the 'fetch' command first.")

    if not filings_to_extract:
        click.echo(
            f"⚠️ No filing subdirectories found to extract for ticker '{ticker}'. The directory '{Path(DEFAULT_FILINGS_DIRECTORY) / sanitize_filename(ticker)}' might be empty or contain no processable items.")
        return

    output_base_dir: Path
    if output:
        output_base_dir = Path(output)
    else:
        output_base_dir = Path(DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY)

    output_base_dir.mkdir(parents=True, exist_ok=True)  # Ensure the base output directory exists

    click.echo(f"📊 Extracting data from {len(filings_to_extract)} filing(s) for '{ticker}' into '{output_base_dir}'...")

    try:
        # Extractor methods expect the raw ticker for internal sanitization and processing
        data_frames_dict = extractor.extract_data(ticker, filings_to_extract)
        extractor.save_to_csv(ticker, data_frames_dict, output_base_dir)
        # Success message handled by save_to_csv
    except Exception as e:
        click.echo(f"❌ An unexpected error occurred during data extraction for '{ticker}': {e}", err=True)
        # import traceback
        # click.echo(traceback.format_exc(), err=True)


if __name__ == "__main__":
    cli()