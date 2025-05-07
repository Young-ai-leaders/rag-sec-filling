import os
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from lxml import etree
from typing import List, Dict, Any
from settings import (
    DEFAULT_FILINGS_DIRECTORY,
    DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY
)

class FilingsExtractor:
    def __init__(self, filings_directory: str = DEFAULT_FILINGS_DIRECTORY) -> None:
        self.filings_directory = filings_directory
    
    def get_company_filings(self, ticker: str) -> List[str]:
        """Discover the names of all the filings for a company ticker."""
        company_dir = f"{self.filings_directory}/{ticker}"
        if not os.path.exists(company_dir):
            raise FileNotFoundError(f"No filings found for {ticker}")
        
        return [filing for filing in os.listdir(company_dir) if os.path.isdir(f"{company_dir}/{filing}")]

    def extract_data(self, ticker: str, filings: List[str]) -> Dict[str, Any]:
        """Extract the financial data from a list of filings."""
        result = {}
        for filing in filings:
            print(f"Extracting {ticker}'s filing: {filing}")
            parsing_result = self._parse_filing(filing)
            if parsing_result is not None:
                result[filing] = parsing_result
        
        return result
        
    def _parse_filing(self, filing_name: str) -> pd.DataFrame | None:
        """Handles the parsing of one specific filing."""
        filing_dir = f"{self.filings_directory}/{ticker}/{filing_name}"
        
        for file in os.listdir(filing_dir):
            if file.endswith("_htm.xml"):
                return self._parse_xbrl(f"{filing_dir}/{file}")
            
            if file.endswith(".htm") and not file.endswith("-index.htm"):
                return self._parse_html(f"{filing_dir}/{file}")
            
    def _parse_xbrl(self, file_path: str) -> pd.DataFrame | None:
        """Handles the parsing of xbrl filing data files."""
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            ns = {
                "xbrli": "http://www.xbrl.org/2003/instance",
                "xbrldi": "http://xbrl.org/2006/xbrldi"
            }
            
            # parse resource defintions
            contexts = {}
            for context in root.findall(".//xbrli:context", ns):
                context_id = context.get("id")
                period = context.find(".//xbrli:period", ns)
                start_date = period.findtext("xbrli:startDate", default=None, namespaces=ns)
                end_date = period.findtext("xbrli:endDate", default=None, namespaces=ns)
                instant = period.findtext("xbrli:instant", default=None, namespaces=ns)
                country = context.findtext(".//xbrldi:explicitMember", default=None, namespaces=ns)
                contexts[context_id] = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "instant": instant,
                    "country": country
                }

            facts = []
            for fact in root.xpath("//*[starts-with(name(), \"us-gaap:\")]", namespaces=ns):
                # ignore none digit values
                if not fact.text or not (fact.text == "-" or fact.text.isdigit()):
                    continue
                
                context = { 
                    "startDate": "", 
                    "endDate": "", 
                    "instant": "",
                    "country": ""
                }
                if fact.get("contextRef") in contexts:
                    context =  contexts[fact.get("contextRef")]
                    
                facts.append({
                    "name": fact.tag.split("}")[1],
                    "value": fact.text,
                    "unitRef": fact.get("unitRef"),
                    "decimals": fact.get("decimals"),
                    "startDate": context["startDate"],
                    "endDate": context["endDate"],
                    "instant": context["instant"],
                    "contry": context["country"]
                })

            return pd.DataFrame(facts)
        except Exception as e:
            print(f"XBRL parsing error: {e}")
            
    def _parse_html(self, file_path: str) -> Dict[str, Any]:
        try:
            # TODO fix html parsing
            # with open(file_path, "r", encoding="utf-8") as f:
            #     soup = BeautifulSoup(f.read(), "html.parser")
            
            # tables = {}
            # for i, table in enumerate(soup.find_all("table")):
            #     try:
            #         df = pd.read_html(StringIO(str(table)))[0]
            #         df = df.dropna(how="all").reset_index(drop=True)
                    
            #         if any("$" in str(x) for x in df.iloc[0]):
            #             df.columns = df.iloc[0]
            #             df = df[1:]
                    
            #         tables[f"table_{i+1}"] = df
            #     except:
            #         continue
            
            return pd.DataFrame()
        except Exception as e:
            print(f"HTML parsing error: {e}")

    def save_to_csv(self, ticker: str, data: Dict[str, pd.DataFrame], output_dir: str = DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY) -> None:
        """Saves the data created by extract data into csv files (one per filing)."""
        if not data:
            print("No data to save.")
            return
        
        output_dir = os.path.join(output_dir, ticker)
        
        os.makedirs(output_dir, exist_ok=True)
        for name, df in data.items():
            if isinstance(df, pd.DataFrame):
                df.to_csv(f"{output_dir}/{name}.csv", index=False)

        print(f"Saved {len(data)} filing/s to {output_dir}")

if __name__ == "__main__":
    extractor = FilingsExtractor()
    ticker = "AAPL"
    filings = extractor.get_company_filings(ticker)
    extracted_data = extractor.extract_data(ticker, filings)
    extractor.save_to_csv(ticker, extracted_data)