DEFAULT_FILINGS_DIRECTORY = "./filings"

FETCHER_BASE_URL = "https://www.sec.gov/Archives/edgar/data"
FETCHER_TICKER_CIK_MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"
FETCHER_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"
FETCHER_HEADERS = {"User-Agent": "Young AI Leaders Linz office@youngaileaderslinz.at"}
DEFAULT_FETCHER_SUPPORTED_FILE_TYPES = (".htm", ".txt", ".xml", ".xsd")
DEFAULT_FETCHER_IGNORED_KEYWORDS = ("companysearch", "-index.htm")

DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY = "./output"