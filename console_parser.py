from filing_parser import FilingParser # if in another module

def run_parser_console(ticker: str) -> None:
    filings_dir = f"./filings/{ticker}"
    parser = FilingParser(filings_directory=filings_dir)

    confirm = input(f"\nDo you want to parse and split all filings in '{filings_dir}'? (y/n): ").strip().lower()
    if confirm == "y":
        output_file = f"parsed_{ticker}_structured.json"
        parser.parse_all_filings_structured(output_file=output_file)  
        print(f"\nExported structured parsed sections to {output_file}")
    else:
        print("Parsing skipped.")