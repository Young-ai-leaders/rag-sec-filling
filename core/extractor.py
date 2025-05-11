import re
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from io import StringIO
from lxml import etree # type: ignore # lxml might not have stubs by default
from typing import Dict, List, Optional

from config.settings import (
    DEFAULT_FILINGS_DIRECTORY,
    DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY
)
from utils.helpers import sanitize_filename # Added import


class FilingsExtractor:
    def __init__(self, filings_directory: str | Path = DEFAULT_FILINGS_DIRECTORY) -> None:
        self.filings_directory = Path(filings_directory)

    def get_company_filings(self, ticker: str) -> List[str]:
        """Get list of filings for a company."""
        safe_ticker = sanitize_filename(ticker) # Use imported sanitize_filename
        company_dir = self.filings_directory / safe_ticker

        if not company_dir.exists() or not company_dir.is_dir(): # Check if it's a directory
            raise FileNotFoundError(f"No filings directory found for {safe_ticker} at {company_dir}")

        
        return [f.name for f in company_dir.iterdir() if f.is_dir()]

    def extract_data(self, ticker: str, filings: List[str]) -> Dict[str, Optional[pd.DataFrame]]:
        """Extract structured data from filings."""
        results: Dict[str, Optional[pd.DataFrame]] = {}
        safe_ticker_for_path = sanitize_filename(ticker) # Sanitize for path construction

        for filing_name in filings: 
            filing_path_dir = self.filings_directory / safe_ticker_for_path / filing_name
            
            if not filing_path_dir.is_dir():
                print(f"⚠️ Expected filing directory not found or is not a directory: {filing_path_dir}")
                results[filing_name] = None
                continue

            parsed_data = self._parse_filing(filing_path_dir) # Pass the directory of the specific filing
            results[filing_name] = parsed_data # Can be None if parsing fails
        return results

    def _parse_filing(self, filing_path_dir: Path) -> Optional[pd.DataFrame]:
        """Parse a single filing directory for XBRL or HTML data."""
        
        xbrl_files = list(filing_path_dir.glob("*_htm.xml"))
        if xbrl_files:
           
            return self._parse_xbrl(xbrl_files[0])

       
        html_files = [
            f for f in filing_path_dir.glob("*.htm") 
            if "-index.htm" not in f.name.lower() and "form" not in f.name.lower() 
        ]
        
        if html_files:
           
            html_files.sort(key=lambda x: len(x.name))
            if html_files: # Ensure list is not empty after filtering
                 return self._parse_html(html_files[0])
        
        print(f"⚠️ No suitable XBRL or HTML file found for parsing in {filing_path_dir}")
        return None

    def _parse_xbrl(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Parse XBRL financial data."""
        try:
            
            parser = etree.XMLParser(recover=True) 
            tree = etree.parse(str(file_path), parser)
            root = tree.getroot()
            
           
            ns = dict(root.nsmap) if root.nsmap else {}
            if None in ns: # Handle default namespace
                ns['defaultns'] = ns.pop(None)

           
            ns.setdefault("xbrli", "http://www.xbrl.org/2003/instance")
            ns.setdefault("us-gaap", "http://fasb.org/us-gaap/2023") 
            ns.setdefault("dei", "http://xbrl.sec.gov/dei/2023")   

            # Context parsing
            contexts = {}
            for context_elem in root.findall(".//xbrli:context", namespaces=ns):
                context_id = context_elem.get("id")
                if not context_id:
                    continue
                period_elem = context_elem.find(".//xbrli:period", namespaces=ns)
                if period_elem is None:
                    contexts[context_id] = {} # Context without period info
                    continue
                
                contexts[context_id] = {
                    "startDate": period_elem.findtext("xbrli:startDate", default=None, namespaces=ns),
                    "endDate": period_elem.findtext("xbrli:endDate", default=None, namespaces=ns),
                    "instant": period_elem.findtext("xbrli:instant", default=None, namespaces=ns),
                }

            
            facts = []
        
            for fact_elem in root.xpath("//*[namespace-uri()!='http://www.xbrl.org/2003/instance' and namespace-uri()!='http://www.w3.org/2001/XMLSchema-instance' and text()]", namespaces=ns):
                if fact_elem.tag.startswith('{http://www.xbrl.org/2003/linkbase}'): # Skip linkbase elements
                    continue

                context_ref = fact_elem.get("contextRef")
                unit_ref = fact_elem.get("unitRef")
                decimals = fact_elem.get("decimals")
                
                value_str = fact_elem.text.strip() if fact_elem.text else None
                
                if value_str and context_ref:
                    numeric_value: Optional[float] = None
                    try:
                        if value_str == "-":
                            numeric_value = None
                        else:
                           
                            numeric_value = float(value_str.replace(',', '')) 
                    except ValueError:
                        
                        if not value_str.lstrip('-').replace('.', '', 1).isdigit(): 
                             pass 

                    context_info = contexts.get(context_ref, {})
                    fact_data = {
                        "name": etree.QName(fact_elem.tag).localname, # Get local name without namespace URI
                        "value": numeric_value,
                        "unit": unit_ref,
                        "decimals": decimals,
                        "startDate": context_info.get("startDate"),
                        "endDate": context_info.get("endDate"),
                        "instant": context_info.get("instant"),
                        # "country": context_info.get("country") # Add if relevant
                    }
                    facts.append(fact_data)

            return pd.DataFrame(facts) if facts else None
        except etree.XMLSyntaxError as e:
            print(f"⚠️ XBRL syntax error in {file_path.name}: {str(e)}")
            return None
        except Exception as e:
            print(f"⚠️ Unexpected error parsing XBRL in {file_path.name}: {str(e)}")
            return None

    def _parse_html(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Parse HTML financial tables. This is a basic implementation."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            soup = BeautifulSoup(content, "html.parser")

            all_dfs = []
            for table_idx, table_tag in enumerate(soup.find_all("table")):
                try:
                  
                    dfs_from_table = pd.read_html(StringIO(str(table_tag)), flavor='bs4', match='.+') 
                    if dfs_from_table:
                        df = dfs_from_table[0] 
                        df = df.dropna(how="all").reset_index(drop=True) 
                        df = df.dropna(axis=1, how="all").reset_index(drop=True)

                        if df.empty or not any("$" in str(cell) or "Consolidated" in str(cell) for _, row in df.head(2).iterrows() for cell in row):
                            if not any(kw in str(table_tag).lower() for kw in ["balance sheet", "income statement", "cash flow", "operations"]):
                                continue # Skip table if it doesn't look financial

                        # Try to set header if first row looks like one
                        if not df.empty and any(isinstance(x, str) and (len(x) > 2 or x.isupper()) for x in df.iloc[0]): # Basic header check
                             if len(df.iloc[0].unique()) > len(df.columns) / 2: # Avoid making data row a header
                                df.columns = df.iloc[0]
                                df = df[1:].reset_index(drop=True)
                        
                        if not df.empty:
                            all_dfs.append(df)
                except ValueError as ve: 
                    pass # Continue to next table
                except Exception as e:
                    print(f"Error parsing table {table_idx + 1} in {file_path.name}: {e}")
                    continue
            
            if all_dfs:
                # For simplicity, concatenate all found "financial-like" tables.
                return pd.concat(all_dfs, ignore_index=True)
            return None
        except Exception as e:
            print(f"⚠️ HTML parsing error in {file_path.name}: {str(e)}")
            return None

    def save_to_csv(self, ticker: str, data: Dict[str, Optional[pd.DataFrame]],
                    output_dir: str | Path = DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY) -> None:
        """Save extracted data to CSV files."""
        safe_ticker_dirname = sanitize_filename(ticker) # Sanitize ticker for directory name
        # Output path will be like ./output/AAPL/
        output_path_for_ticker = Path(output_dir) / safe_ticker_dirname
        output_path_for_ticker.mkdir(parents=True, exist_ok=True)

        saved_files_count = 0
        for filing_name, df in data.items(): # filing_name is accession number
            if df is not None and not df.empty:
                # filing_name is already filesystem-safe (e.g., '0001193125-23-020410')
                # No need to sanitize filing_name further if it's already an accession number.
                # If filing_name could contain special characters, then sanitize it:
                # clean_filing_name = sanitize_filename(filing_name)
                csv_file_path = output_path_for_ticker / f"{filing_name}.csv"
                try:
                    df.to_csv(csv_file_path, index=False)
                    saved_files_count += 1
                except Exception as e:
                    print(f"Error saving DataFrame for {filing_name} to CSV: {e}")
           

        if saved_files_count > 0:
            print(f"💾 Saved {saved_files_count} filings' data to CSVs in {output_path_for_ticker}")
        else:
            print(f"No data was extracted or suitable for saving to CSV for ticker {ticker}.")