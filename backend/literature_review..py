import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# summary of a single paper's key aspects
@dataclass
class PaperSummary:
    pdf_id: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    methodology: Optional[str] = None
    key_findings: List[str] = field(default_factory=list)
    limitations: Optional[str] = None
    domain: Optional[str] = None

# result of comparing multiple papers
@dataclass 
class ComparisonResult:
    pdf_ids: List[str]
    similarities: List[str]
    differences: List[str]
    key_themes: List[str]
    methodology_comparison: Optional[str] = None
    raw_context: Optional[Dict] = None

# result of synthesizing findings across papers
@dataclass
class SynthesisResult:
    synthesis: str
    citations: List[Dict[str, Any]]
    methodology_comparison: Optional[str] = None
    findings_comparison: Optional[str] = None
    confidence: str = "medium"
    papers_analyzed: List[str] = field(default_factory=list)

# structured literature review output
@dataclass
class LiteratureReviewReport:
    title: str
    papers: List[PaperSummary]
    themes: List[Dict[str, Any]]
    synthesis: str
    methodology_overview: str
    gaps_and_future_work: str
    references: List[str]
    format: str = "markdown"