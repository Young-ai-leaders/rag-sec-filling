from __future__ import annotations
import json
from typing import List
import pandas as pd

from sec_analyzer.utils import chunk_text


def process_csv_original_method(csv_path: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Merge the entire CSV into one string, then chunk."""
    df = pd.read_csv(csv_path, keep_default_na=False)
    df["combined"] = df.apply(lambda row: " ".join(row.astype(str)), axis=1)
    full_text = " ".join(df["combined"].tolist())
    chunks = chunk_text(full_text, max_length=chunk_size, overlap=overlap)
    return chunks


def process_csv_to_natural_language(csv_path: str) -> List[str]:
    """Convert each CSV row to a compact natural-language sentence."""
    df = pd.read_csv(csv_path, keep_default_na=False)
    chunks: List[str] = []
    for _, row in df.iterrows():
        parts = []
        name = row.get("name")
        value = row.get("value")
        unit = row.get("unit")
        end_date = row.get("endDate")
        if name: parts.append(f"the metric is '{name}'")
        if value: parts.append(f"its value is {value}")
        if unit: parts.append(f"with unit '{unit}'")
        if end_date: parts.append(f"as of {end_date}")
        if len(parts) > 1:
            chunks.append("For a financial record, " + ", ".join(parts) + ".")
    return chunks


def process_csv_to_raw_string(csv_path: str) -> List[str]:
    """Use each CSV row as a raw string chunk."""
    df = pd.read_csv(csv_path, keep_default_na=False)
    df["combined"] = df.apply(lambda row: " ".join(row.astype(str)), axis=1)
    return df["combined"].tolist()


def get_text_from_parsed_json(json_path: str) -> str:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    blobs = []
    for parsed_file in data:
        for _section_name, section_text in parsed_file.get("sections", {}).items():
            blobs.append(section_text)
    return "\n\n".join(blobs)


def chunk_unstructured_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    return chunk_text(text, max_length=chunk_size, overlap=overlap)