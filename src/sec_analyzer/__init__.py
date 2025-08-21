# src/sec_analyzer/__init__.py

"""
SEC Analyzer package.

This package provides tools to fetch, parse, and extract data from SEC filings,
and to process this data for vector-based semantic search.
"""

from .scraper.fetcher import FilingsFetcher
from .scraper.parser import FilingParser
from .scraper.extractor import FilingsExtractor

__all__ = [
    "FilingsFetcher",
    "FilingParser",
    "FilingsExtractor",
]

__version__ = "0.1.0"