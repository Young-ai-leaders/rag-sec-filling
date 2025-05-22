
class Filing:
    def __init__(self, cik, ticker, filing_type, year, text_chunks, source, embeddings=None):

        self.cik = cik
        self.ticker = ticker
        self.filing_type = filing_type
        self.year = year
        self.text_chunks = text_chunks
        self.source = source
        self.embeddings = embeddings


    def __repr__(self):
        return f"Filing(cik={self.cik}, ticker={self.ticker}, filing_type={self.filing_type}, year={self.year}, source={self.source})"


    def to_json(self):
        return {
            "cik": self.cik,
            "ticker": self.ticker,
            "filing_type": self.filing_type,
            "year": self.year,
            "text_chunks": self.text_chunks,
            "source": self.source,
            "embeddings": self.embeddings
        }

