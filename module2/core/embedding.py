from transformers import AutoTokenizer, AutoModel

from module2.classes.Filing import Filing
from module2.utils.utils import embed_filing

if __name__ == "__main__":
    # Example usage
    cik = "0000320193"
    ticker = "AAPL"
    filing_type = "10-K"
    year = "2023"
    chunks = ["This is a test sentence.", "This is another test sentence."]
    source = "https://www.sec.gov/Archives/edgar/data/320193/000032019323000012/aapl-20230930.htm"
    filing = Filing(cik, ticker, filing_type, year, chunks, source)
    tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-small-en')
    model = AutoModel.from_pretrained('BAAI/bge-small-en')
    embeddings = embed_filing(filing, model, tokenizer)
    filing.embeddings = embeddings.numpy()
    print("Json for mongoDB", filing.to_json())