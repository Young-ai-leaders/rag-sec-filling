# src/sec_analyzer/utils.py
"""
Shared utility functions for the SEC Analyzer package.

This module contains helper functions for:
- Filesystem operations (sanitizing names, creating directories)
- Data validation and cleaning (years, financial values)
- Network operations (retry decorator)
- Text processing (chunking, hashing)
"""

import hashlib
import os
import re
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, List, Optional

import requests

# It's good practice to import constants from a central config
# to avoid circular dependencies if utils were ever imported by config.
# For now, defining them here is fine if they are only for the retry decorator.
MAX_RETRIES = 3
RETRY_DELAY = 1.5  # Seconds


# --- Filesystem and Path Helpers ---

def sanitize_filename(name: str) -> str:
    """Sanitize strings for safe filesystem use."""
    if not isinstance(name, str):
        name = str(name)  # Ensure it's a string
    name = name.strip()
    name = re.sub(r'[^\w\-_.]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name if name else "_sanitized_empty_name_"

def create_directory(path: str | Path) -> Path:
    """Create directory if it does not exist."""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


# --- Data Validation and Cleaning ---

def validate_years(years_str_list: List[str]) -> Optional[List[int]]:
    """Convert and validate a list of year strings."""
    if not years_str_list:
        return None
    
    valid_years = set()
    current_year = time.localtime().tm_year
    for y_str in years_str_list:
        y_str = y_str.strip()
        if y_str.isdigit():
            year = int(y_str)
            if 1900 <= year <= current_year + 1:
                valid_years.add(year)
            else:
                print(f"Warning: Year {year} is out of typical range, skipping.")
        elif y_str:
            print(f"Warning: Invalid year format '{y_str}', skipping.")
            
    return sorted(list(valid_years)) if valid_years else None

def clean_financial_value(value: Any) -> Optional[float]:
    """Convert financial strings (e.g., '$1,234', '(567)') to numeric values."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    cleaned_value = value.strip()
    if not cleaned_value or cleaned_value.lower() == 'n/a' or cleaned_value == '-':
        return None
    
    cleaned_value = cleaned_value.replace('$', '').replace(',', '').replace('£', '').replace('€', '')
    is_negative = False
    if cleaned_value.startswith('(') and cleaned_value.endswith(')'):
        is_negative = True
        cleaned_value = cleaned_value[1:-1]
    
    try:
        numeric_val = float(cleaned_value)
        return -numeric_val if is_negative else numeric_val
    except ValueError:
        return None


# --- Network Helpers ---

DecoratedFunc = Callable[..., Any]

def handle_retry(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY) -> Callable[[DecoratedFunc], DecoratedFunc]:
    """Decorator to retry network operations with exponential backoff."""
    def decorator(func: DecoratedFunc) -> DecoratedFunc:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            last_exception = None
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    retries += 1
                    if retries >= max_retries:
                        print(f"Max retries ({max_retries}) reached for {func.__name__}. Last error: {e}")
                        raise
                    actual_delay = delay * (2 ** (retries - 1))
                    print(f"Retry {retries}/{max_retries} for {func.__name__} after error: {e}. Waiting {actual_delay:.2f}s...")
                    time.sleep(actual_delay)
                except Exception as e:
                    print(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            return None
        return wrapper
    return decorator


# --- Text Processing Helpers ---

def chunk_text(text: str, max_length: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split a long string into overlapping chunks of text.
    
    Args:
        text: The input string to be chunked.
        max_length: The maximum number of characters in each chunk.
        overlap: The number of characters to overlap between consecutive chunks.
        
    Returns:
        A list of text chunks.
    """
    if max_length <= 0:
        raise ValueError("max_length must be > 0")
    if overlap < 0 or overlap >= max_length:
        raise ValueError("overlap must be >= 0 and < max_length")

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_length, len(text))
        chunks.append(text[start:end])
        start += (max_length - overlap)
    return chunks

def hash_text(s: str) -> str:
    """Generate a stable SHA256 hash for a string, useful for deduplication."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()