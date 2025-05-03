import os
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Any

from settings import (
    DEFAULT_FILINGS_DIRECTORY,
    DEFAULT_FETCHER_SUPPORTED_FILE_TYPES,
    DEFAULT_FETCHER_IGNORED_KEYWORDS,
    FETCHER_HEADERS,
    FETCHER_BASE_URL,
    FETCHER_SUBMISSIONS_URL,
    FETCHER_TICKER_CIK_MAPPING_URL,
)

NUM_OLDEST_FILINGS = 4

class FilingsFetcher:
    def __init__(self, 
                 filings_directory: str = DEFAULT_FILINGS_DIRECTORY,
                 supported_file_types: List[str] = DEFAULT_FETCHER_SUPPORTED_FILE_TYPES,
                 ignored_keywords: List[str] = DEFAULT_FETCHER_IGNORED_KEYWORDS) -> None:
        self.filings_directory = filings_directory
        self.supported_file_types = supported_file_types
        self.ignored_keywords = ignored_keywords
    
    def get_cik_from_ticker(self, ticker: str) -> str | None:
        """Get CIK number from stock ticker symbol."""
        try:
            response = requests.get(FETCHER_TICKER_CIK_MAPPING_URL, headers=FETCHER_HEADERS)
            response.raise_for_status()
            ticker_map = response.json() # The JSON is in format {index: {"cik_str": ..., "ticker": ..., "title": ...}}
            
            for company in ticker_map.values():
                if company["ticker"].upper() == ticker.upper():
                    return str(company["cik_str"]).zfill(10)
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch ticker-CIK mapping: {e}")

    def _get_metadata(self, cik: str, company: str) -> Dict[str, Any] | None:
        """Get the metadata by cik."""
        try:
            url = FETCHER_SUBMISSIONS_URL.format(cik)
            print(f"\nFetching metadata for {company} (CIK: {cik}) from {url}...")
    
            response = requests.get(url, headers=FETCHER_HEADERS)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to get metadata: {e}")

    def _get_accession_numbers(self, metadata: Dict[str, Any], years: List[str]) -> List[Tuple[str, str]]:
        """Extracts the relevant accession numbers from the retrieved metadata."""
        metadata_recent = metadata['filings']['recent']
        filings = zip(
            metadata_recent['accessionNumber'],
            metadata_recent['form'],
            metadata_recent['reportDate']
        )
        match_expression = lambda form, reportDate: form == '10-K' and (years is None or reportDate[:4] in years)
        return [(accNumber, accNumber.replace("-", "")) for accNumber, form, reportDate in filings if match_expression(form, reportDate)][:NUM_OLDEST_FILINGS]

    def _get_file_index(self, index_url: str, accession_dashed: str, index_file_path: str) -> List[Dict]:
        """Creates a index.csv file and returns the filing file information in dict format."""
        try:
            response = requests.get(index_url, headers=FETCHER_HEADERS)
            response.raise_for_status()
            file_index = []
        
            with open(index_file_path, 'w', encoding='utf-8') as f:
                f.write("\"File Name\",\"File URL\"\n")
                f.write(f"\"Index URL\",\"{index_url}\"\n")
                for link in BeautifulSoup(response.content, features="html.parser").find_all('a', href=True):
                    relative_url = link['href']
                    file_name = relative_url.split('/')[-1]
                    
                    # Skip unwanted files
                    if (not relative_url.lower().endswith(self.supported_file_types) or
                        any(kw in relative_url.lower() for kw in self.ignored_keywords) or
                        file_name.lower() == f"{accession_dashed}-index.htm".lower()):
                        continue
                    
                    full_url = f"https://www.sec.gov{relative_url}"
                    f.write(f"\"{file_name}\",\"{full_url}\"\n")
                    file_index.append({
                        "file_name" : file_name,
                        "full_url": full_url
                        })
            
            return file_index
        except requests.exceptions.RequestException as e:
            print(f"Failed to download index page: {e}")

    def _get_file(self, url: str, file_path: str) -> bool:
        """Downloads a certain file identified by a url."""
        try:
            with requests.get(url, headers=FETCHER_HEADERS, stream=True) as response:
                response.raise_for_status()
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {url}: {e}")
            return False

    def get_filings(self, cik: str, ticker: str | None, years: List[str]) -> None:
        """Handles the filing extraction/download process."""
        company = ticker or "Unknown_Company"
        cik_stripped = cik.lstrip("0")
        metadata = self._get_metadata(cik, company)
        accession_numbers = self._get_accession_numbers(metadata, years)

        for accession_dashed, accession_clean in accession_numbers:
            filing_url = f"{FETCHER_BASE_URL}/{cik_stripped}/{accession_clean}"
            index_url = f"{filing_url}/{accession_dashed}-index.htm"
            company_filing_dir = f"{self.filings_directory}/{company}/{accession_dashed}"
            index_file_path = f"{company_filing_dir}/index.csv"

            print(f"Processing filing: {index_url}, Company: {company}")
            
            # Create directory for filing
            os.makedirs(company_filing_dir, exist_ok=True)

            for file_info in self._get_file_index(index_url, accession_dashed, index_file_path):
                print(f"    Downloading: {file_info['file_name']}")
                file_path = f"{company_filing_dir}/{file_info['file_name']}"
                if not self._get_file(file_info["full_url"], file_path):
                    print(f"    Failed to download: {file_info['file_name']}")

if __name__ == "__main__":
    ticker = "AAPL"
    filings_fetcher = FilingsFetcher()
    cik = filings_fetcher.get_cik_from_ticker(ticker)
    filings_fetcher.get_filings(cik, ticker, ['2024'])