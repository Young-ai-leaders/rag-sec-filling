# src/sec_analyzer/__init__.py

"""
SEC Analyzer package.

This package provides tools to fetch, parse, and extract data from SEC filings,
and to process this data for vector-based semantic search.
"""

# Lazy imports to avoid circular import issues
def __getattr__(name):
    if name == "FilingsFetcher":
        from .scraper.fetcher import FilingsFetcher
        return FilingsFetcher
    elif name == "FilingParser":
        from .scraper.parser import FilingParser
        return FilingParser
    elif name == "FilingsExtractor":
        from .scraper.extractor import FilingsExtractor
        return FilingsExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__version__ = "0.1.0"