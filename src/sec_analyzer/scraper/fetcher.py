# src/module1_scraper/fetcher.py
import os
import re
import requests  
import json  
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path  # Added Path here

from sec_analyzer.config import (
    DEFAULT_FILINGS_DIRECTORY,
    DEFAULT_FETCHER_SUPPORTED_FILE_TYPES,
    DEFAULT_FETCHER_IGNORED_KEYWORDS,
    FETCHER_HEADERS,
    FETCHER_BASE_URL,
    FETCHER_SUBMISSIONS_URL,
    FETCHER_TICKER_CIK_MAPPING_URL,
)
from sec_analyzer.utils import sanitize_filename, create_directory


class FilingsFetcher:
    def __init__(self,
                 filings_directory: str = DEFAULT_FILINGS_DIRECTORY,
                 supported_file_types: List[str] = DEFAULT_FETCHER_SUPPORTED_FILE_TYPES,
                 ignored_keywords: List[str] = DEFAULT_FETCHER_IGNORED_KEYWORDS) -> None:
        self.filings_directory_path = Path(filings_directory)  # Store as Path object
        # Ensure supported_file_types is a tuple for string methods like .endswith
        self.supported_file_types_tuple = tuple(st.lower() for st in supported_file_types)
        self.ignored_keywords_lower = [kw.lower() for kw in ignored_keywords]

    def get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK number from stock ticker symbol."""
        try:
            response = requests.get(FETCHER_TICKER_CIK_MAPPING_URL, headers=FETCHER_HEADERS)
            response.raise_for_status()
            ticker_map_data = response.json()

            for _key, company_info in ticker_map_data.items():  # Iterate through dict items
                if isinstance(company_info, dict) and company_info.get("ticker", "").upper() == ticker.upper():
                    return str(company_info["cik_str"]).zfill(10)
            print(f"Ticker '{ticker.upper()}' not found in SEC mapping.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch ticker-CIK mapping: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to decode ticker-CIK mapping JSON: {e}")
            return None
        except Exception as e:  # Catch any other unexpected error during mapping
            print(f"An unexpected error occurred while getting CIK for ticker {ticker}: {e}")
            return None

    def _get_metadata(self, cik: str, company_name_for_log: str) -> Optional[Dict[str, Any]]:
        """Get the metadata by CIK. Expects a 10-digit zero-padded CIK."""
        if not (cik.isdigit() and len(cik) == 10):
            print(f"Error: _get_metadata received an invalid CIK: {cik}. Must be 10 digits.")
            return None
        try:
            # URL requires the 10-digit zero-padded CIK.
            # FETCHER_SUBMISSIONS_URL is "https://data.sec.gov/submissions/CIK{}.json"
            url = FETCHER_SUBMISSIONS_URL.format(cik)

            print(f"\nFetching metadata for {company_name_for_log} (CIK: {cik}) from {url}...")

            response = requests.get(url, headers=FETCHER_HEADERS, timeout=20)  # Added timeout
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"Metadata fetch HTTP error for CIK {cik} from {url}: {e}")
            if e.response is not None:
                print(
                    f"Response status: {e.response.status_code}, Response text: {e.response.text[:500]}...")  # Show some response
            return None
        except requests.exceptions.RequestException as e:  # Other network errors
            print(f"Metadata fetch network error for CIK {cik} from {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Metadata JSON decode error for CIK {cik} from {url}: {e}")
            return None

    def _get_accession_numbers(self, metadata: Dict[str, Any], years: Optional[List[int]], num_filings: int) -> List[
        Tuple[str, str]]:
        """Extracts the relevant accession numbers from the retrieved metadata."""
        if not metadata or "filings" not in metadata or "recent" not in metadata["filings"]:
            print("Debug: Metadata is missing 'filings' or 'filings.recent' keys.")
            return []

        metadata_recent = metadata["filings"]["recent"]
        required_keys = ["accessionNumber", "form", "reportDate"]
        for key in required_keys:
            if key not in metadata_recent:
                print(f"Debug: Metadata 'filings.recent' is missing key: '{key}'")
                return []
            if not isinstance(metadata_recent[key], list):
                print(f"Debug: Metadata key '{key}' is not a list.")
                return []
            if len(metadata_recent[key]) != len(metadata_recent["accessionNumber"]):
                print(f"Debug: Metadata key '{key}' has inconsistent length with 'accessionNumber'.")
                return []

        if not metadata_recent["accessionNumber"]:
            print("Debug: 'filings.recent.accessionNumber' is empty. No recent filings to process.")
            return []

        filings_data = zip(
            metadata_recent["accessionNumber"],
            metadata_recent["form"],
            metadata_recent["reportDate"]
        )

        match_expression = lambda form_type, report_date_str: (
                form_type == "10-K" and
                (years is None or (
                            report_date_str and len(report_date_str) >= 4 and report_date_str[:4].isdigit() and int(
                        report_date_str[:4]) in years))
        )

        filtered_accessions = []
        processed_filing_count = 0
        matched_filing_count = 0

        for acc_number, form_type, report_date_str in filings_data:
            processed_filing_count += 1
            if matched_filing_count >= num_filings:
                break

            if match_expression(form_type, report_date_str):
                accession_dashed = str(acc_number)  # Should already be string from JSON
                accession_clean = accession_dashed.replace("-", "")
                filtered_accessions.append((accession_dashed, accession_clean))
                matched_filing_count += 1

        if not filtered_accessions:
            print("Debug: No 10-K filings matched the criteria from the recent filings list.")
            print(f"Debug: Years filter was: {years}")
            print(f"Debug: Processed {processed_filing_count} entries from metadata_recent.")
            print(f"Debug: Desired number of filings was: {num_filings}")
            print("Debug: First few entries from metadata_recent it iterated over (up to 5):")
            for i in range(min(5, len(metadata_recent["accessionNumber"]))):
                acc = metadata_recent['accessionNumber'][i]
                form = metadata_recent['form'][i]
                date_val = metadata_recent['reportDate'][i]
                should_match = match_expression(form, date_val)
                print(
                    f"  - acc: {acc}, form: {form}, date: {date_val} (Should match for 10-K in {years}? {'Yes' if should_match else 'No'})")

        return filtered_accessions

    def _get_file_index(self, index_url: str, accession_dashed: str, index_file_path_str: str) -> List[Dict[str, str]]:
        """Creates a index.csv file and returns the filing file information in dict format."""
        file_index_list: List[Dict[str, str]] = []
        try:
            print(f"    Fetching file index: {index_url}")
            response = requests.get(index_url, headers=FETCHER_HEADERS, timeout=20)
            response.raise_for_status()

            index_file_path = Path(index_file_path_str)
            create_directory(index_file_path.parent)

            with open(index_file_path, "w", encoding="utf-8") as f:
                f.write("\"File Name\",\"File URL\"\n")
                f.write(f"\"Index URL\",\"{index_url}\"\n")

                soup = BeautifulSoup(response.content, "html.parser")
                table = soup.find("table", class_="tableFile")  # Main table with files
                links_to_check_from_table = []
                if table:
                    links_to_check_from_table = table.find_all("a", href=True)


                all_potential_links = soup.find_all("a", href=True)

                # Combine and unique-ify links by href to avoid processing duplicates
                combined_links_map: Dict[str, Any] = {}  # Store link tag by href
                for link_tag in links_to_check_from_table + all_potential_links:
                    href = link_tag.get("href")
                    if href and href not in combined_links_map:
                        combined_links_map[href] = link_tag

                processed_urls = set()

                for original_href, link in combined_links_map.items():
                    href_to_process = original_href
                    is_ixbrl_doc = False


                    if href_to_process.startswith("/ix?doc="):

                        try:

                            from urllib.parse import urlparse, parse_qs
                            parsed_ix_url = urlparse(href_to_process)
                            doc_param = parse_qs(parsed_ix_url.query).get('doc')
                            if doc_param and doc_param[0]:
                                href_to_process = doc_param[
                                    0]
                                is_ixbrl_doc = True

                            else:
                                print(f"    Warning: Could not parse 'doc' from iXBRL link: {original_href}")
                                continue
                        except Exception as e_parse:
                            print(f"    Warning: Error parsing iXBRL link {original_href}: {e_parse}")
                            continue


                    file_name = os.path.basename(href_to_process)
                    if not file_name:

                        link_text_name = sanitize_filename(link.get_text(strip=True))
                        if link_text_name and any(
                                link_text_name.lower().endswith(st) for st in self.supported_file_types_tuple):
                            file_name = link_text_name
                        else:

                            continue

                    # File type and keyword filtering
                    if (not file_name.lower().endswith(self.supported_file_types_tuple) or
                            any(kw in file_name.lower() for kw in self.ignored_keywords_lower) or
                            file_name.lower() == f"{accession_dashed.lower()}-index.htm"):

                        if file_name.lower() == f"{accession_dashed.lower()}-index.htm" and not is_ixbrl_doc:

                            continue
                        elif not file_name.lower().endswith(self.supported_file_types_tuple):

                            continue


                    full_url: str
                    if href_to_process.startswith("/Archives/"):
                        full_url = f"https://www.sec.gov{href_to_process}"
                    elif href_to_process.startswith("http://") or href_to_process.startswith("https://"):
                        full_url = href_to_process
                    elif href_to_process.startswith("/"):
                        full_url = f"https://www.sec.gov{href_to_process}"
                    else:
                        base_of_index_url = index_url.rsplit('/', 1)[0]
                        full_url = f"{base_of_index_url}/{href_to_process}"


                    if full_url in processed_urls:
                        continue
                    processed_urls.add(full_url)

                    f.write(f"\"{file_name}\",\"{full_url}\"\n")
                    file_index_list.append({
                        "file_name": file_name,
                        "full_url": full_url
                    })
            return file_index_list
        except requests.exceptions.RequestException as e:
            print(f"    Failed to download index page {index_url}: {e}")
            return file_index_list
        except Exception as e:
            print(f"    An unexpected error occurred in _get_file_index for {index_url}: {e}")
            return file_index_list

    def _get_file(self, url: str, file_path_str: str) -> bool:
        """Downloads a file if it doesn't already exist."""
        file_path_obj = Path(file_path_str)
        if file_path_obj.exists() and file_path_obj.stat().st_size > 0:  # Check if not empty
            print(f"      File exists and is not empty: {file_path_obj.name}")
            return True
        try:
            print(f"      Downloading: {file_path_obj.name} from {url}")
            with requests.get(url, headers=FETCHER_HEADERS, stream=True, timeout=30) as response:
                response.raise_for_status()
                # Ensure parent directory exists before writing
                create_directory(file_path_obj.parent)
                with open(file_path_obj, "wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        file_handle.write(chunk)
            return True
        except requests.exceptions.RequestException as e:
            print(f"      Failed to download {url}: {e}")
            if file_path_obj.exists():
                try:
                    file_path_obj.unlink(missing_ok=True)  # Python 3.8+
                except TypeError:  # For older Python if missing_ok not available
                    if file_path_obj.exists(): file_path_obj.unlink()
            return False
        except Exception as e:
            print(f"      An unexpected error occurred in _get_file for {url}: {e}")
            return False

    def get_filings(self, cik: str, ticker: Optional[str], years: Optional[List[int]], num_filings: int = 4) -> None:
        """Handles the filing extraction/download process."""

        if not (cik.isdigit() and len(cik) == 10):
            raise ValueError(f"Invalid CIK provided to get_filings: '{cik}'. Must be a 10-digit number.")

        company_name_for_log = ticker if ticker else f"CIK_{cik}"
        safe_company_dirname = sanitize_filename(company_name_for_log)

        metadata = self._get_metadata(cik, company_name_for_log)
        if not metadata:
            print(f"Failed to retrieve or parse metadata for {company_name_for_log}. Download process cannot start.")
            return

        accession_numbers = self._get_accession_numbers(metadata, years, num_filings)
        if not accession_numbers:
            print(
                f"No matching filings found for {company_name_for_log} (CIK: {cik}) based on the criteria. Download process will not start.")
            return

        print(f"Found {len(accession_numbers)} filing(s) to process for {company_name_for_log}.")
        download_attempted_count = 0

        for accession_dashed, accession_clean in accession_numbers:
            cik_stripped_for_path = cik.lstrip("0")  # Used for edgar/data/... URLs

            filing_base_url = f"{FETCHER_BASE_URL}/{cik_stripped_for_path}/{accession_clean}"
            index_url = f"{filing_base_url}/{accession_dashed}-index.htm"

            company_filing_dir = self.filings_directory_path / safe_company_dirname / accession_dashed
            create_directory(company_filing_dir)

            index_file_path_str = str(company_filing_dir / "index.csv")

            print(f"  Processing filing: {accession_dashed} (Index: {index_url})")

            files_to_download = self._get_file_index(index_url, accession_dashed, index_file_path_str)
            if not files_to_download:
                print(f"    No downloadable files found or index fetch failed for {accession_dashed}.")
                continue

            download_attempted_count += 1  # Considered an attempt if we get files to download

            for file_info in files_to_download:
                file_path_str = str(
                    company_filing_dir / sanitize_filename(file_info["file_name"]))  # Sanitize downloaded filename
                if not self._get_file(file_info["full_url"], file_path_str):
                    print(f"    Failed to download: {file_info['file_name']} for filing {accession_dashed}")
            print(f"  Finished processing files for filing: {accession_dashed}")

        if download_attempted_count > 0:
            print(f"\n✅ Download process completed for {download_attempted_count} filing(s) of {company_name_for_log}.")
            print(f"   Filings should be in subdirectories under: {self.filings_directory_path / safe_company_dirname}")
        elif accession_numbers:  # We found accession numbers but didn't attempt downloads (e.g. all index fetches failed)
            print(
                f"\n⚠️ Found {len(accession_numbers)} filings but failed to process their file indexes for {company_name_for_log}.")
        # If accession_numbers was empty, the message is handled earlier.


