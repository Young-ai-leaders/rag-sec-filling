# SEC API Configuration
FETCHER_BASE_URL = "https://www.sec.gov/Archives/edgar/data"
FETCHER_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"
FETCHER_TICKER_CIK_MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"
# In config/settings.py
FETCHER_HEADERS = {
    "User-Agent": "MySECLearningProject YourName your.email@example.com",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive"
}

# File Handling
DEFAULT_FILINGS_DIRECTORY = "./filings"
DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY = "./output"
DEFAULT_FETCHER_SUPPORTED_FILE_TYPES = (".htm", ".html", ".xml", ".xsd", ".txt") # Added .txt
DEFAULT_FETCHER_IGNORED_KEYWORDS = ("companysearch", "-index.htm", "xslForm", "form.xsd") # Added form.xsd

# Text Processing (These might be for later modules)
# CHUNK_SIZE = 512  # For text splitting
# CHUNK_OVERLAP = 50
MAX_RETRIES = 3
RETRY_DELAY = 1.5  # Seconds
