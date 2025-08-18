# src/sec_analyzer/utils.py
import os
import re
import time
from pathlib import Path
from functools import wraps
import requests
from typing import List, Optional, Any, Callable # Added Any, Callable

# It's good practice to import constants from a central config if they are shared
from config.settings import MAX_RETRIES, RETRY_DELAY # Import from settings

def sanitize_filename(name: str) -> str:
    """Sanitize strings for safe filesystem use."""
    if not isinstance(name, str):
        name = str(name) # Ensure it's a string
    # Remove leading/trailing whitespace first
    name = name.strip()
    # Replace non-alphanumeric (excluding hyphen, underscore, period) with underscore
    name = re.sub(r'[^\w\-_.]', '_', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores that might result from replacements
    name = name.strip('_')
    # If the name becomes empty after sanitization (e.g., "."), provide a default
    return name if name else "_sanitized_empty_name_"

def validate_years(years_str_list: List[str]) -> Optional[List[int]]:
    """Convert and validate year strings."""
    if not years_str_list:
        return None # Or [] if an empty list is preferred for no years
    
    valid_years = set()
    current_year = time.localtime().tm_year
    for y_str in years_str_list:
        y_str = y_str.strip()
        if y_str.isdigit():
            year = int(y_str)
            # Add reasonable validation for year, e.g., within a certain range
            if 1900 <= year <= current_year + 1: # Allow for future filings sometimes
                valid_years.add(year)
            else:
                print(f"Warning: Year {year} is out of typical range, skipping.")
                # return None # Or be strict and invalidate all if one is bad
        elif y_str: # If not digit and not empty string
            print(f"Warning: Invalid year format '{y_str}', skipping.")
            # return None # Or be strict
            
    return sorted(list(valid_years)) if valid_years else None

def create_directory(path: str | Path) -> Path:
    """Create directory if not exists."""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

# Type hint for the decorated function and its arguments/return type
DecoratedFunc = Callable[..., Any]

def handle_retry(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY) -> Callable[[DecoratedFunc], DecoratedFunc]:
    """Retry decorator for network operations."""
    def decorator(func: DecoratedFunc) -> DecoratedFunc:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            last_exception = None
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e: # Be more specific about retryable exceptions
                    last_exception = e
                    retries += 1
                    if retries >= max_retries:
                        print(f"Max retries ({max_retries}) reached for {func.__name__}. Last error: {e}")
                        raise # Re-raise the last exception
                    actual_delay = delay * (2 ** (retries -1)) # Exponential backoff
                    print(f"Retry {retries}/{max_retries} for {func.__name__} after error: {e}. Waiting {actual_delay:.2f}s...")
                    time.sleep(actual_delay)
                except Exception as e: # Catch other non-retryable exceptions from func
                    print(f"Non-retryable error in {func.__name__}: {e}")
                    raise # Re-raise immediately
            return None # Should not be reached if max_retries > 0 and an exception is always raised or value returned
        return wrapper
    return decorator

def clean_financial_value(value: Any) -> Optional[float]:
    """Convert financial strings (and other types) to numeric values."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        # Could attempt str(value) or return None / raise error
        return None 

    cleaned_value = value.strip()
    if not cleaned_value or cleaned_value.lower() == 'n/a' or cleaned_value == '-':
        return None
    
    # Remove currency symbols, parentheses for negatives, commas
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

# Need to import requests if using requests.exceptions.RequestException
import requests # Add this import if not already present in the actual file context
