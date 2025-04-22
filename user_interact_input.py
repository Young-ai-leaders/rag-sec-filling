import requests
import os
from bs4 import BeautifulSoup

# Configuration
NUM_OLDEST_FILINGS = 4
HEADERS = {'User-Agent': 'Your Name your.email@example.com'}
BASE_URL = "https://www.sec.gov/Archives/edgar/data"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"
SUPPORTED_FILE_TYPES = ('.htm', '.txt', '.xml', '.xsd')
IGNORED_KEYWORDS = ('companysearch', '-index.htm')
TICKER_CIK_MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"


def get_cik_from_ticker(ticker):
    """Get CIK number from stock ticker symbol."""
    try:
        response = requests.get(TICKER_CIK_MAPPING_URL, headers=HEADERS)
        response.raise_for_status()
        ticker_map = response.json()
        
        # The JSON is in format {index: {"cik_str": ..., "ticker": ..., "title": ...}}
        for company in ticker_map.values():
            if company["ticker"].upper() == ticker.upper():
                return str(company["cik_str"]).zfill(10)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch ticker-CIK mapping: {e}")
        return None

def get_valid_company_input():
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
            cik = get_cik_from_ticker(ticker)
            if cik:
                return ticker.upper(), cik
            print(f"Ticker '{ticker}' not found. Please try again or enter CIK directly.")


def fetch_metadata(cik, company):
    url = SUBMISSIONS_URL.format(cik)
    print(f"\nFetching metadata for {company} (CIK: {cik}) from {url}...")
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to get metadata: {e}")
        exit()

def get_accession_numbers(metadata, company, cik, years=None):
    filings = metadata['filings']['recent']
    return [
        (acc, acc.replace("-", ""))
        for acc, form, date in zip(
            filings['accessionNumber'],
            filings['form'],
            filings['reportDate']
        )
        if form == '10-K' and (years is None or date[:4] in years)
    ][:NUM_OLDEST_FILINGS]

def download_file(url, file_path):
    try:
        with requests.get(url, headers=HEADERS, stream=True) as response:
            response.raise_for_status()
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return False

def process_filing(company, cik_stripped, accession_dashed, accession_clean):
    filing_url = f"{BASE_URL}/{cik_stripped}/{accession_clean}"
    index_url = f"{filing_url}/{accession_dashed}-index.htm"
    
    print(f"Processing filing: {index_url}, Company: {company}")
    
    try:
        response = requests.get(index_url, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to download index page: {e}")
        return

    # Create directory for filing
    company_filing_dir = f"filings/{company}/{accession_dashed}"
    os.makedirs(company_filing_dir, exist_ok=True)
    
    # Initialize index file
    index_file_path = f"{company_filing_dir}/index.txt"
    with open(index_file_path, 'w', encoding='utf-8') as f:
        f.write(f"Index URL: {index_url}\n\nFile Name,File URL\n")

    # Parse index page and download files
    soup = BeautifulSoup(response.content, 'html.parser')
    
    for link in soup.find_all('a', href=True):
        file_url_relative = link['href']
        file_name = file_url_relative.split('/')[-1]
        
        # Skip unwanted files
        if (not file_url_relative.lower().endswith(SUPPORTED_FILE_TYPES) or
            any(kw in file_url_relative.lower() for kw in IGNORED_KEYWORDS) or
            file_name.lower() == f"{accession_dashed}-index.htm".lower()):
            continue
        
        print(f"  Downloading: {file_name}")
        full_file_url = f"https://www.sec.gov{file_url_relative}"
        file_path = f"{company_filing_dir}/{file_name}"
        
        if download_file(full_file_url, file_path):
            with open(index_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{file_name},{full_file_url}\n")

def main():
    # Get company input
    ticker, cik = get_valid_company_input()
    cik_stripped = cik.lstrip("0")
    
    # Get additional filters
    years_input = input("Enter years to filter (comma separated, leave empty for all): ").strip()
    years = [y.strip() for y in years_input.split(',')] if years_input else None
    
    # Fetch and process filings
    metadata = fetch_metadata(cik, ticker or "Unknown Company")
    accession_numbers = get_accession_numbers(metadata, ticker or "Unknown Company", cik, years)
    
    for accession_dashed, accession_clean in accession_numbers:
        process_filing(ticker or "Unknown_Company", cik_stripped, accession_dashed, accession_clean)
    
    print(f"\nAll filings for {ticker or cik} have been downloaded.")

if __name__ == "__main__":
    main()