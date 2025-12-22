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

# retrieve all chunks for a specific paper from Pinecone
def get_paper_chunks(
    pdf_id: str,
    section_filter: Optional[List[str]] = None,
    max_chunks: int = 50,
) -> List[Dict[str, Any]]:
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)
    
    stats = index.describe_index_stats()
    dimension = stats.dimension
    dummy_vector = [0.0] * dimension
    
    # query with metadata filter
    results = index.query(
        vector=dummy_vector,
        top_k=max_chunks,
        include_metadata=True,
        filter={"pdf_id": {"$eq": pdf_id}}
    )
    
    chunks = []
    for match in results.matches:
        metadata = match.metadata or {}
        section = metadata.get("section", "Unknown")
        
        # apply section filter if provided
        if section_filter:
            if not any(s.lower() in section.lower() for s in section_filter):
                continue
        
        chunks.append({
            "id": match.id,
            "text": metadata.get("text", ""),
            "section": section,
            "chunk_type": metadata.get("chunk_type", "unknown"),
            "pdf_id": pdf_id,
            "score": match.score,
        })
    
    return chunks

# extract text from specific sections of a paper
def get_section_text(pdf_id: str, section_keywords: List[str]) -> str:
    chunks = get_paper_chunks(pdf_id)
    
    matching_chunks = []
    for chunk in chunks:
        section = chunk.get("section", "").lower()
        if any(kw.lower() in section for kw in section_keywords):
            matching_chunks.append(chunk)
    
    # sort by chunk position
    matching_chunks.sort(key=lambda x: x.get("id", ""))
    
    return "\n\n".join(c["text"] for c in matching_chunks)

# get abstract of a paper
def get_abstract(pdf_id: str) -> str:
    return get_section_text(pdf_id, ["abstract", "summary"])

# get the methodology section
def get_methodology(pdf_id: str) -> str:
    return get_section_text(pdf_id, ["method", "methodology", "materials", "procedure", "approach"])

# get the results section
def get_results(pdf_id: str) -> str:
    return get_section_text(pdf_id, ["result", "finding", "outcome", "evaluation"])

# get the conclusion section
def get_conclusion(pdf_id: str) -> str:
    return get_section_text(pdf_id, ["conclusion", "discussion", "summary"])
