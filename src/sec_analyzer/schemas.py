from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class Filing:
    cik: str
    ticker: str
    filing_type: str
    year: int
    source: str
    text_chunk: Optional[str] = None
    embedding: Optional[List[float]] = None

    def to_mongo(self) -> Dict[str, Any]:
        return asdict(self)