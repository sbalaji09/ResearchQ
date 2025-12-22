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

# extract and summarize the methodology section of a paper
def extract_methodology_summary(pdf_id: str) -> Dict[str, Any]:
    methodology_text = get_methodology(pdf_id)
    
    if not methodology_text or len(methodology_text) < 50:
        return {
            "pdf_id": pdf_id,
            "summary": "Methodology section not found or too short.",
            "research_design": None,
            "participants": None,
            "data_collection": None,
            "analysis_method": None,
            "error": "insufficient_content"
        }
    
    # truncate if too long
    if len(methodology_text) > 8000:
        methodology_text = methodology_text[:8000] + "..."
    
    prompt = f"""Analyze this methodology section from a research paper and extract key information.

        METHODOLOGY TEXT:
        {methodology_text}

        Provide a structured summary with these components (if available):
        1. Research Design: (quantitative/qualitative/mixed, experimental/observational, etc.)
        2. Participants/Sample: (who, how many, how selected)
        3. Data Collection: (what data, how collected, instruments used)
        4. Analysis Method: (statistical tests, qualitative coding, etc.)
        5. Key Procedures: (main steps of the study)

        Format your response as:
        RESEARCH_DESIGN: [1-2 sentences]
        PARTICIPANTS: [1-2 sentences]  
        DATA_COLLECTION: [1-2 sentences]
        ANALYSIS_METHOD: [1-2 sentences]
        SUMMARY: [2-3 sentence overall summary]

        If any component is not mentioned, write "Not specified" for that field."""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.3,
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # parse the response
    def extract_field(text: str, field_name: str) -> Optional[str]:
        import re
        pattern = rf"{field_name}:\s*(.+?)(?=\n[A-Z_]+:|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value if value.lower() != "not specified" else None
        return None
    
    return {
        "pdf_id": pdf_id,
        "research_design": extract_field(result_text, "RESEARCH_DESIGN"),
        "participants": extract_field(result_text, "PARTICIPANTS"),
        "data_collection": extract_field(result_text, "DATA_COLLECTION"),
        "analysis_method": extract_field(result_text, "ANALYSIS_METHOD"),
        "summary": extract_field(result_text, "SUMMARY") or result_text,
        "raw_text_length": len(methodology_text),
    }

# compare 2-5 papers to find similarities and differences
def compare_papers(pdf_ids: List[str]) -> ComparisonResult:
    if len(pdf_ids) < 2:
        raise ValueError("Need at least 2 papers to compare")
    if len(pdf_ids) > 5:
        raise ValueError("Maximum 5 papers can be compared at once")
    
    # get content from each paper
    paper_contents = {}
    for pdf_id in pdf_ids:
        abstract = get_abstract(pdf_id)
        methodology = get_methodology(pdf_id)
        conclusion = get_conclusion(pdf_id)
        
        # combine key sections
        content = f"""
            ABSTRACT:
            {abstract[:1500] if abstract else "Not found"}

            METHODOLOGY:
            {methodology[:1500] if methodology else "Not found"}

            CONCLUSION:
            {conclusion[:1500] if conclusion else "Not found"}
            """
        paper_contents[pdf_id] = content
    
    # comparison prompt
    papers_text = ""
    for pdf_id, content in paper_contents.items():
        papers_text += f"\n{'='*40}\nPAPER: {pdf_id}\n{'='*40}\n{content}\n"
    
    prompt = f"""Compare these {len(pdf_ids)} research papers and identify:

        {papers_text}

        Provide your analysis in this exact format:

        SIMILARITIES:
        - [List 3-5 similarities across the papers]

        DIFFERENCES:
        - [List 3-5 key differences between the papers]

        KEY_THEMES:
        - [List 3-5 themes that emerge from these papers together]

        METHODOLOGY_COMPARISON:
        [1-2 paragraphs comparing the methodological approaches]

        Be specific and cite which papers you're referring to when noting differences."""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.4,
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # parse the response
    def extract_list(text: str, section_name: str) -> List[str]:
        import re
        pattern = rf"{section_name}:\s*\n((?:[-•*]\s*.+\n?)+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            items = re.findall(r"[-•*]\s*(.+)", match.group(1))
            return [item.strip() for item in items if item.strip()]
        return []
    
    def extract_paragraph(text: str, section_name: str) -> str:
        import re
        pattern = rf"{section_name}:\s*\n(.+?)(?=\n[A-Z_]+:|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
    
    return ComparisonResult(
        pdf_ids=pdf_ids,
        similarities=extract_list(result_text, "SIMILARITIES"),
        differences=extract_list(result_text, "DIFFERENCES"),
        key_themes=extract_list(result_text, "KEY_THEMES"),
        methodology_comparison=extract_paragraph(result_text, "METHODOLOGY_COMPARISON"),
        raw_context={"paper_contents": paper_contents}
    )