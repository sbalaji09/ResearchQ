from dataclasses import dataclass, field
import datetime
from typing import Dict, List, Optional


@dataclass
class PaperReference:
    title: str
    authors: List[str]
    year: int
    pdf_id: str

@dataclass
class LiteratureReviewResult:
    title: Optional[str] = None
    abstract: Optional[str] = None
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    discussion: Optional[str] = None
    limitations: Optional[str] = None
    future_work: Optional[str] = None
    conclusion: Optional[str] = None

    citations: List[Dict[str, str]] = field(default_factory=list)

    model: Optional[str] = None              
    domain: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(datetime.timezone.utc).isoformat()
    )