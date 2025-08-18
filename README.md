# SEC Filing Analysis Engine (RAG Pipeline)

This project is a community initiative to build a RAG (Retrieval Augmented Generation) pipeline for querying and analyzing company data from SEC filings. The system allows users to ask natural language questions about companies and receive accurate, context-aware answers sourced directly from their financial disclosures.

## Project Goal

The ultimate goal is to create a system where a user can ask a question like, "What were Apple's main risk factors in 2023?" or "Compare Microsoft's and Google's R&D spending over the last three years," and receive a precise, data-backed answer.

## Current Status

The foundational data pipeline is complete. The system can now fetch SEC filings, process them into structured data, load them into a vector database, and perform semantic searches.

*   **Module 1: Web Scraper & Data Extractor (✅ Completed)**
*   **Module 2: Vector Database Integration (✅ Completed)**
*   **Module 3: RAG Pipeline Implementation (⏳ Upcoming)**
*   **Module 4: Evaluation Framework (⏳ Upcoming)**

## Features

### Module 1: Data Acquisition & Extraction
*   **Fetch Filings:** Download 10-K filings for any company using its ticker symbol or CIK.
*   **Filter by Year:** Specify particular years or the number of recent filings to retrieve.
*   **Extract Structured Data:** Automatically parse XBRL data from filings into clean, structured CSV files containing financial facts.
*   **Parse Textual Data:** Extract the complete text from "Item 8: Financial Statements" and save it in a structured JSON format, ready for NLP tasks.

### Module 2: Vector Database & Search
*   **Ingest Data:** Process and chunk structured CSV data into a format suitable for semantic search.
*   **Generate Embeddings:** Use state-of-the-art Hugging Face models to convert financial data into high-dimensional vector embeddings.
*   **Vector Storage:** Upsert the data and its embeddings into a MongoDB Atlas collection.
*   **Semantic Search:** Perform powerful vector similarity searches to find the most relevant financial facts based on natural language questions.
*   **Metadata Filtering:** Filter search results by `ticker` and `year` to narrow down queries with high precision.

## Tech Stack
*   **Python 3.8+**
*   **Command-Line Interface:** [Click](https://click.palletsprojects.com/)
*   **Web Scraping:** [Requests](https://requests.readthedocs.io/), [Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
*   **Data Parsing:** [lxml](https://lxml.de/), [Pandas](https://pandas.pydata.org/)
*   **Vector Database:** [MongoDB Atlas Vector Search](https://www.mongodb.com/products/platform/atlas-vector-search)
*   **Embedding Models:** [Hugging Face Transformers](https://huggingface.co/docs/transformers/index) (`BAAI/bge-small-en`)
*   **Database Driver:** [PyMongo](https://pymongo.readthedocs.io/)

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone (https://github.com/Young-ai-leaders/rag-sec-filling.git)
    cd rag-sec-filling
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install click requests beautifulsoup4 pandas lxml transformers torch pymongo python-dotenv
    ```
    *(Note: For GPU support with PyTorch, follow the official installation instructions.)*

4.  **Configure Environment Variables:**
    Create a file named `.env` in the project's root directory and add your credentials.
    ```ini
    # .env
    MONGODB_URI="your_mongodb_atlas_connection_string"
    DB_NAME="sec_filling"
    COLLECTION_NAME="embedded_chunks"
    SEARCH_INDEX_NAME="vector_index"
    MODEL_NAME="BAAI/bge-small-en"
    ```

5.  **Set SEC User-Agent:**
    The SEC requires a custom User-Agent for all requests. Open `src/sec_analyzer/config.py` and update the `FETCHER_HEADERS` with your information:
    ```python
    FETCHER_HEADERS = {
        "User-Agent": "YourCompanyName YourName your.email@example.com",
        # ...
    }
    ```

6.  **Set up MongoDB Atlas:**
    *   Ensure you have a MongoDB Atlas cluster running.
    *   After you run the `ingest` command for the first time, you must manually create the Vector Search Index on the collection. See the project documentation for the required JSON configuration.

## Usage (Command-Line Interface)

The entire pipeline is controlled through `cli.py`.

### Example Workflow: Analyzing Apple's 2023 10-K

**Step 1: Fetch the filing**
```bash
python cli.py fetch --ticker AAPL --years 2023 --num-filings 1
```

**Step 2: Extract structured XBRL data into a CSV**
```bash
python cli.py extract --ticker AAPL
```
*This will create a file at `output/AAPL/0000320193-23-000106.csv`.*

**Step 3: Ingest the CSV into the vector database**
```bash
python cli.py ingest --csv output/AAPL/0000320193-23-000106.csv --ticker AAPL --cik 0000320193 --year 2023
```

This will populate your MongoDB Atlas collection.

**Step 4: Create the Vector Search Index in the Atlas UI**  
Follow the project documentation to create the `vector_index` on the `sec_filling.embedded_chunks` collection using the correct JSON definition.

**Step 5: Query your data!**
```bash
python cli.py query --q "What was the value for Accounts Receivable?" --ticker AAPL
```

**Expected Output:**
```
Found 5 result(s):

 score=0.9327 | AAPL (2023)
For a financial record, the metric is 'AccountsPayableCurrent', its value is 62611000000.0, with unit 'usd'.
------------------------------------------------------------

 score=0.9312 | AAPL (2023)
For a financial record, the metric is 'AccountsReceivableNetCurrent', its value is 28184000000.0, with unit 'usd'.
------------------------------------------------------------
...
```

## Future Work

* **Module 3 (RAG Pipeline):** Integrate a Large Language Model (LLM) to take the search results and generate a human-readable, conversational answer.
* **Module 4 (Evaluation):** Build a framework to evaluate the accuracy and relevance of the answers generated by the RAG pipeline.
