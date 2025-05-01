from filing_fetcher import FilingsFetcher
from typing import List, Tuple

def get_valid_company_input(filings_fetcher: FilingsFetcher) -> Tuple[str | None, str]:
    """Get valid company ticker or CIK from user."""
    while True:
        ticker = input("Enter company ticker symbol (e.g. AAPL) or CIK (e.g. 0000320193): ").strip()
        
        # If input is all digits, treat as CIK
        if ticker.isdigit():
            if len(ticker) <= 10:
                return None, ticker.zfill(10)  # (ticker, cik)
            print("CIK must be 10 digits or less. Try again.")
        
        # Otherwise treat as ticker symbol
        else:
            cik = filings_fetcher.get_cik_from_ticker(ticker)
            if cik:
                return ticker.upper(), cik
            print(f"Ticker '{ticker}' not found. Please try again or enter CIK directly.")

def get_years() -> List[str]:
    years_input = input("Enter years to filter (comma separated, leave empty for all): ").strip()
    return [y.strip() for y in years_input.split(',')] if years_input else None

filings_fetcher = FilingsFetcher()
ticker, cik = get_valid_company_input(filings_fetcher)
years = get_years()
filings_fetcher.get_filings(cik, ticker, years)
print(f"\nAll filings for {ticker or cik} have been downloaded.")