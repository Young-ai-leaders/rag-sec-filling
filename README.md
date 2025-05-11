# SEC Filing Analysis Engine (RAG Pipeline Initiative) - WIP

This project is a community initiative to build a RAG (Retrieval Augmented Generation) pipeline for querying and analyzing company data from SEC filings. The project is structured into four distinct modules:

1.  **Module 1: Web Scraper & Data Extractor (✅ Completed - Refinements Pending)**
2.  **Module 2: Vector Database Integration (⏳ Upcoming)**
3.  **Module 3: RAG Pipeline Implementation (⏳ Upcoming)**
4.  **Module 4: Evaluation Framework (⏳ Upcoming)**

**Current Status: Module 1 is functionally complete, allowing users to fetch, parse, and extract data from SEC 10-K filings. Further refinements and robust error handling for this module are planned.**

## Project Goal

The ultimate goal is to create a system where users can ask natural language questions about companies (e.g., "What were Apple's revenues in 2023?", "Summarize Microsoft's main risk factors.") and receive accurate, context-aware answers sourced directly from their SEC filings.

## Module 1: Web Scraper & Data Extractor

This initial module provides the foundational capabilities to acquire and preprocess data from the SEC EDGAR database.

### Features

*   **Fetch Filings:**
    *   Download 10-K filings for a specified company using its ticker symbol or CIK (Central Index Key).
    *   Filter filings by specific years.
    *   Specify the number of recent filings to retrieve.
    *   Saves downloaded files (HTML, TXT, XBRL components) locally in an organized directory structure.
*   **Parse Filings:**
    *   Extracts the textual content of "Item 8. Financial Statements and Supplementary Data" from downloaded 10-K filings (both `.txt` and iXBRL `.htm` versions).
    *   Splits the extracted Item 8 text into subsections (e.g., Consolidated Statements of Operations, Balance Sheets, Cash Flows, Notes).
    *   Saves the parsed textual data as a structured JSON file, ideal for later use in a RAG pipeline (chunking and embedding).
*   **Extract Data:**
    *   Extracts structured financial data directly from XBRL components of the filings.
    *   Prioritizes XBRL instance documents (e.g., `*_htm.xml` or iXBRL within the main `.htm` document).
    *   Saves the extracted structured data (XBRL facts including concept names, values, units, and periods) into CSV files, one per filing.

### Tech Stack (Module 1)

*   Python 3.8+
*   [Click](https://click.palletsprojects.com/): For the command-line interface.
*   [Requests](https://requests.readthedocs.io/): For making HTTP requests to SEC EDGAR.
*   [Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/): For parsing HTML content (used in the text parser and for the index page of filings).
*   [lxml](https://lxml.de/): For parsing XBRL (XML) data.
*   [Pandas](https://pandas.pydata.org/): For handling and saving structured data (CSVs).

### File Structure (Module 1 Output)

*   **Fetched Filings:** `filings/<TICKER>/<ACCESSION_NUMBER>/<files...>`
*   **Parsed Textual Data:** `output/parsed_<TICKER>.json`
*   **Extracted Structured Data:** `output/<TICKER>/<ACCESSION_NUMBER>.csv`

### Setup & Installation (Module 1)

1.  **Clone the repository (if applicable):**

    git clone <your-repo-url>
    cd <your-repo-name>

2.  **Create and activate a virtual environment (recommended):**

    python -m venv .venv
    # On Windows:
    # .venv\Scripts\activate
    # On macOS/Linux:
    # source .venv/bin/activate

3.  **Install dependencies:**

    pip install click requests beautifulsoup4 pandas lxml
    # Or, if a requirements.txt is provided:
    # pip install -r requirements.txt

4.  **Configure User-Agent:**
    *   Open `config/settings.py`.
    *   Update the `FETCHER_HEADERS` dictionary with a valid `User-Agent` string. The SEC requires this for API access.

        FETCHER_HEADERS = {
            "User-Agent": "YourProjectName YourName youremail@example.com", # <-- IMPORTANT: UPDATE THIS
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }

### Usage (Module 1 CLI)

The main entry point is `cli.py`.

**1. Fetch Filings:**

    python cli.py fetch --ticker <TICKER_SYMBOL> --years <YEARS> --num-filings <NUMBER>
    # OR
    python cli.py fetch --cik <CIK_NUMBER> --years <YEARS> --num-filings <NUMBER>

*   `--ticker`: Company stock ticker (e.g., AAPL).
*   `--cik`: Company CIK (10-digit, will be zero-padded).
*   `--years`: Comma-separated years (e.g., `2022,2023`). Optional.
*   `--num-filings`: Number of recent 10-K filings to fetch. Defaults to 4.

**Example:**

    python cli.py fetch --ticker AAPL --years 2023 --num-filings 1

**2. Parse Filings (Textual Item 8):**

(Run after fetching filings for the ticker)

    python cli.py parse <TICKER_SYMBOL>

*   `<TICKER_SYMBOL>`: The ticker for which filings were downloaded.

**Example:**

    python cli.py parse AAPL

Output: `output/parsed_AAPL.json`

**3. Extract Data (Structured XBRL to CSV):**

(Run after fetching filings for the ticker)

    python cli.py extract <TICKER_SYMBOL>

*   `<TICKER_SYMBOL>`: The ticker for which filings were downloaded.

**Example:**

    python cli.py extract AAPL

Output: `output/AAPL/<ACCESSION_NUMBER>.csv`

### Planned Refinements for Module 1

*   More robust filtering of non-filing links during the `fetch` process.
*   Enhanced error handling and logging across all components.
*   Improved heuristics for HTML table extraction in the `FilingsExtractor` if XBRL is not available or for older filings.
*   Further cleaning of text extracted by the `FilingParser` (e.g., removing page numbers, excessive whitespace).
*   Comprehensive unit and integration tests.

## Contributing

This is a community initiative! Details on how to contribute to upcoming modules will be provided soon. For Module 1, feedback and bug reports are welcome.

