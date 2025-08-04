
class Filing:
    def __init__(self, cik, ticker, filing_type, year, source,text_chunk = None, embedding=None):

        self.cik = cik
        self.ticker = ticker
        self.filing_type = filing_type
        self.year = year
        self.text_chunk = text_chunk
        self.source = source
        self.embedding = embedding


    def __repr__(self):
        return f"Filing(cik={self.cik}, ticker={self.ticker}, filing_type={self.filing_type}, year={self.year}, source={self.source})"


    def to_json(self):
        return {
            "cik": self.cik,
            "ticker": self.ticker,
            "filing_type": self.filing_type,
            "year": self.year,
            "text_chunk": self.text_chunk,
            "source": self.source,
            "embedding": self.embedding
        }

