
"""HOW TO USE:
1. Save filings in ./filings/[TICKER]/[ACCESSION_NUMBER]/
   (e.g., ./filings/AAPL/0000320193-20-000096/)

2. Run the script:

3. Outputs will be saved in ./output/

METHODS:
- get_company_filings(ticker): Lists available filings
- extract_tables(ticker, filing): Extracts tables
- save_to_csv(data, output_dir): Saves results

DEFAULT STRUCTURE:
filings/
├── AAPL/
│   └── 0000320193-20-000096/
│       ├── filing1.xml
│       └── filing2.htm
output/
├── financial_data.csv
└── table_1.csv

NOTES:
- For XBRL: Looks for *_htm.xml files
- For HTML: Skips index files, detects $ as currency
- Handles most common table formats"""





import os
import pandas as pd
from bs4 import BeautifulSoup
from lxml import etree

class SECExtractor:
    def __init__(self, data_dir='./filings'):
        self.data_dir = data_dir
    
    def get_company_filings(self, ticker):
        company_dir = f"{self.data_dir}/{ticker}"
        if not os.path.exists(company_dir):
            raise FileNotFoundError(f"No filings found for {ticker}")
        return [f for f in os.listdir(company_dir) if os.path.isdir(f"{company_dir}/{f}")]

    def extract_tables(self, ticker, filing):
        filing_dir = f"{self.data_dir}/{ticker}/{filing}"
        results = {}
        
        for file in os.listdir(filing_dir):
            if file.endswith('_htm.xml'):
                xbrl_data = self._parse_xbrl(f"{filing_dir}/{file}")
                if xbrl_data:
                    results.update(xbrl_data)
                    results['source'] = 'xbrl'
                    return results
        
        for file in os.listdir(filing_dir):
            if file.endswith('.htm') and not file.endswith('-index.htm'):
                html_data = self._parse_html(f"{filing_dir}/{file}")
                if html_data:
                    results.update(html_data)
                    results['source'] = 'html'
                    return results
        
        return results

    def _parse_xbrl(self, file_path):
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            ns = {'xbrli': 'http://www.xbrl.org/2003/instance'}
            
            facts = []
            for elem in root.xpath('//*[@contextRef]', namespaces=ns):
                facts.append({
                    'name': elem.tag.split('}')[-1],
                    'value': elem.text,
                    'context': elem.get('contextRef')
                })
            
            if facts:
                df = pd.DataFrame(facts)
                return {'financial_data': df.pivot(index='context', columns='name', values='value')}
        except Exception as e:
            print(f"XBRL Error: {e}")
        return {}

    def _parse_html(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            tables = {}
            for i, table in enumerate(soup.find_all('table')):
                try:
                    df = pd.read_html(str(table))[0]
                    df = df.dropna(how='all').reset_index(drop=True)
                    
                    if any('$' in str(x) for x in df.iloc[0]):
                        df.columns = df.iloc[0]
                        df = df[1:]
                    
                    tables[f'table_{i+1}'] = df
                except:
                    continue
            
            return tables
        except Exception as e:
            print(f"HTML Error: {e}")
        return {}

    def save_to_csv(self, data, output_dir='./output'):
        os.makedirs(output_dir, exist_ok=True)
        for name, df in data.items():
            if isinstance(df, pd.DataFrame):
                df.to_csv(f"{output_dir}/{name}.csv", index=False)

if __name__ == "__main__":
    extractor = SECExtractor()
    ticker = "AAPL"
    filings = extractor.get_company_filings(ticker)
    
    if filings:
        latest_filing = filings[0]
        print(f"Extracting {ticker}'s filing: {latest_filing}")
        extracted_data = extractor.extract_tables(ticker, latest_filing)
        extractor.save_to_csv(extracted_data)
        print(f"Saved {len(extracted_data)-1} tables to ./output/")
    else:
        print(f"No filings found for {ticker}")