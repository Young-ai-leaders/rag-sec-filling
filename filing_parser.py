import os
from filing_fetcher import FilingsFetcher
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Any
import re
import json
class FilingParser:
    def __init__(self, filings_directory: str) -> None:
        self.filings_directory = "./filings"
        self.supported_file_types = ('.htm', '.html', '.txt')
        self.section_patterns = [
            r"Item\s+8\.*\s*Financial Statements.*?",
            r"Financial Statements and Supplementary Data"
        ]

    def parse_section(self, file_path: str) -> str | None:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            text = soup.get_text(separator="\n", strip=True)
            lines = text.splitlines()

            start_idx = None
            end_idx = None

            for i, line in enumerate(lines):
                if start_idx is None and re.match(r"ITEM\s+8[\.\s]+FINANCIAL STATEMENTS", line.strip(), re.IGNORECASE):
                    start_idx = i
                elif start_idx is not None and re.match(r"ITEM\s+9[\.\s]+", line.strip(), re.IGNORECASE):
                    end_idx = i
                    break

            if start_idx is not None:
                section_lines = lines[start_idx:end_idx] if end_idx else lines[start_idx:]
                return "\n".join(section_lines).strip()

            return None

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    @staticmethod
    def split_subsections(text: str) -> dict:
        sections = {
            "operations": r"CONSOLIDATED STATEMENTS OF OPERATIONS",
            "comprehensive_income": r"CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME",
            "balance_sheet": r"CONSOLIDATED BALANCE SHEETS",
            "shareholders_equity": r"CONSOLIDATED STATEMENTS OF SHAREHOLDERS.*EQUITY",
            "cash_flows": r"CONSOLIDATED STATEMENTS OF CASH FLOWS",
            "notes": r"Notes to Consolidated Financial Statements",
        }
        results = {}
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


    def parse_all_filings_structured(self, output_file: str) -> None:
        parsed_data = []
        for root, _, files in os.walk(self.filings_directory):
            for file in files:
                if file.lower().endswith(self.supported_file_types):
                    file_path = os.path.join(root, file)
                    print(f"Parsing: {file_path}")
                    section_text = self.parse_section(file_path)
                    if section_text:
                        split = self.split_subsections(section_text)
                        parsed_data.append({"file": file_path, "sections": split})

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, indent=2)
    
    def save_parsed_sections_to_json(self, parsed_data: List[Tuple[str, str]], output_file: str) -> None:
        output = [{"file": path, "section": section} for path, section in parsed_data]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    
    
