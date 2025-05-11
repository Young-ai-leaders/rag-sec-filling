# core/parser.py
import os
import re
import json
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Any # Tuple, Dict, Any are not used, can be removed if not planned
from pathlib import Path
from config.settings import DEFAULT_FILINGS_DIRECTORY, DEFAULT_EXTRACTOR_OUTPUT_DIRECTORY

class FilingParser:
    def __init__(self, filings_directory: str = DEFAULT_FILINGS_DIRECTORY):
        self.filings_directory = Path(filings_directory)
        self.supported_file_types = ('.htm', '.html', '.txt') 
        self.section_patterns = [ 
            r"ITEM\s+8[\s\-–]+Financial Statements",
            r"ITEM\s+8[\s\-–]+FINANCIAL STATEMENTS",
            r"Financial Statements and Supplementary Data"
        ]

    def parse_section(self, file_path: str | Path) -> str | None:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                soup = BeautifulSoup(content, "html.parser")


            text = soup.get_text(separator="\n", strip=True)
            lines = text.splitlines()

            start_idx = None
            end_idx = None

            # Regex updated for more robustness and case-insensitivity
            item_8_pattern = re.compile(r"ITEM\s+8[\s\-–.:]*FINANCIAL STATEMENTS", re.IGNORECASE)
            item_9_pattern = re.compile(r"ITEM\s+9[\sA-Z\.–.:]*", re.IGNORECASE) # Matches ITEM 9, ITEM 9A, ITEM 9. etc.


            for i, line in enumerate(lines):
                if start_idx is None and item_8_pattern.match(line.strip()):
                    start_idx = i
                elif start_idx is not None and item_9_pattern.match(line.strip()):
                    end_idx = i
                    break
            
            if start_idx is not None:
                section_lines = lines[start_idx:end_idx] if end_idx is not None else lines[start_idx:]
                return "\n".join(section_lines).strip()
            
           
            return None 

        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return None
        except Exception as e:
            print(f"Unexpected error parsing {file_path}: {e}")
            return None

    @staticmethod
    def split_subsections(text: str) -> dict[str, str]:
        sections = {
            "operations": r"CONSOLIDATED STATEMENTS OF OPERATIONS",
            "comprehensive_income": r"CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME",
            "balance_sheet": r"CONSOLIDATED BALANCE SHEETS",
            "shareholders_equity": r"CONSOLIDATED STATEMENTS OF SHAREHOLDERS.*EQUITY", # Added .* for flexibility
            "cash_flows": r"CONSOLIDATED STATEMENTS OF CASH FLOWS",
            "notes": r"Notes to Consolidated Financial Statements",
        }
        results = {}
        # Use re.IGNORECASE for robustness in finding subsection titles
        for name, pattern in sections.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                results[name] = match.start()
        
        sorted_items = sorted(results.items(), key=lambda x: x[1])
        structured = {}
        for i, (key, start) in enumerate(sorted_items):
            end = sorted_items[i + 1][1] if i + 1 < len(sorted_items) else len(text)
            structured[key] = text[start:end].strip()
        return structured

    def parse_all_filings_structured(self, ticker_filings_path: Path, output_file: str | Path) -> None:
        if not ticker_filings_path.exists():
            raise FileNotFoundError(f"Directory {ticker_filings_path} not found")

        # Count matching files within the specific ticker's directory
        total_files = sum(
            1 for file_path in ticker_filings_path.rglob('*') # Iterate within specific_filings_path
            if file_path.is_file() and
            file_path.suffix.lower() in self.supported_file_types
        )
        if total_files == 0:
            print(f"No supported files found in {ticker_filings_path} to parse.")
            # Create an empty JSON file or handle as preferred
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            print(f"✅ Saved empty result to {output_file}")
            return

        print(f"⏳ Parsing {total_files} filings from {ticker_filings_path}...")

        parsed_data = []
        processed_files = 0

        # Process files from the specific ticker's directory
        for file_path in ticker_filings_path.rglob('*'): # Iterate within specific_filings_path
            if file_path.is_file() and file_path.suffix.lower() in self.supported_file_types:
                processed_files += 1
                print(f"📄 [{processed_files}/{total_files}] Processing: {file_path.name}")

                section_text = self.parse_section(file_path)
                if section_text:
                    parsed_data.append({
                        "file": str(file_path), # Storing relative or absolute path might be a choice
                        "sections": self.split_subsections(section_text)
                    })
                else:
                    print(f"    No 'ITEM 8' section found in {file_path.name}")


        # Save results
        output_file = Path(output_file) # Ensure it's a Path object
        output_file.parent.mkdir(parents=True, exist_ok=True) # Ensure parent directory exists
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, indent=2)
        print(f"✅ Saved {len(parsed_data)} parsed documents to {output_file}")