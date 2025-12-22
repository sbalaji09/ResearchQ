import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
from query_improved import query_with_section_boost
import re

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

# generates a synthesis of findings across papers
def synthesize_findings(
    pdf_ids: List[str],
    focus_question: Optional[str] = None,
) -> SynthesisResult:
    if not focus_question:
        focus_question = "What are the main findings, contributions, and conclusions of these papers? How do they relate to each other?"
    
    # retrieve relevant chunks from all papers
    results = query_with_section_boost(
        question=focus_question,
        top_k=15,  # Get more chunks for synthesis
        boost_factor=2.0,
        use_reranking=True,
        pdf_ids=pdf_ids,
    )
    
    if not results:
        return SynthesisResult(
            synthesis="No relevant content found in the specified papers.",
            citations=[],
            papers_analyzed=pdf_ids,
            confidence="low",
        )
    
    chunks_by_paper = defaultdict(list)
    for r in results:
        doc_id = r.get("metadata", {}).get("pdf_id", "unknown")
        chunks_by_paper[doc_id].append(r)
    
    # build synthesis prompt with organized chunks
    chunks_text = ""
    citations = []
    citation_id = 1
    
    for pdf_id in pdf_ids:
        if pdf_id in chunks_by_paper:
            chunks_text += f"\n\n--- PAPER: {pdf_id} ---\n\n"
            for chunk in chunks_by_paper[pdf_id][:5]:  # Max 5 per paper
                text = chunk.get("text", "")
                section = chunk.get("section", "Unknown")
                
                citations.append({
                    "id": citation_id,
                    "document": pdf_id,
                    "section": section,
                    "text": text[:500] + "..." if len(text) > 500 else text,
                })
                
                chunks_text += f"[{citation_id}] (Section: {section})\n{text}\n\n"
                citation_id += 1
    
    # methodology summaries for comparison
    methodology_summaries = []
    for pdf_id in pdf_ids:
        method_summary = extract_methodology_summary(pdf_id)
        if method_summary.get("summary") and "not found" not in method_summary["summary"].lower():
            methodology_summaries.append(f"**{pdf_id}**: {method_summary['summary']}")
    
    methodology_comparison = "\n".join(methodology_summaries) if methodology_summaries else None
    
    # generate synthesis
    synthesis_prompt = f"""You are synthesizing research findings from {len(pdf_ids)} academic papers.

        FOCUS QUESTION: {focus_question}

        EXCERPTS FROM PAPERS:
        {chunks_text}

        INSTRUCTIONS:
        1. Synthesize the main findings and insights across all papers
        2. Identify common themes and patterns
        3. Note any contradictions or debates between papers
        4. Use citations [1], [2], etc. to reference specific claims
        5. Organize your synthesis thematically, not paper-by-paper
        6. Be comprehensive but concise (aim for 3-4 paragraphs)

        Write a well-organized synthesis that a researcher could use to understand the collective insights from these papers."""

    response = openai_client.chat.completions.create(
        model="gpt-4o",  # Use stronger model for synthesis
        messages=[{"role": "user", "content": synthesis_prompt}],
        max_tokens=1500,
        temperature=0.4,
    )
    
    synthesis_text = response.choices[0].message.content.strip()
    
    # findings comparison
    findings_prompt = f"""Based on these paper excerpts, create a brief comparison of the key findings:

        {chunks_text[:4000]}

        Format as a bulleted list highlighting:
        - What each paper found
        - How findings agree or disagree
        - Overall pattern of results"""

    findings_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": findings_prompt}],
        max_tokens=500,
        temperature=0.3,
    )
    
    findings_comparison = findings_response.choices[0].message.content.strip()
    
    return SynthesisResult(
        synthesis=synthesis_text,
        citations=citations,
        methodology_comparison=methodology_comparison,
        findings_comparison=findings_comparison,
        papers_analyzed=pdf_ids,
        confidence="high" if len(results) >= 10 else "medium",
    )

# generate a complete structured literature review report
def generate_review_report(
    pdf_ids: List[str],
    title: Optional[str] = None,
    format: str = "markdown",
) -> LiteratureReviewReport:
    if not pdf_ids:
        raise ValueError("No papers provided for review")
    
    # generate summaries for each paper
    paper_summaries = []
    for pdf_id in pdf_ids:
        abstract = get_abstract(pdf_id)
        methodology = extract_methodology_summary(pdf_id)
        conclusion = get_conclusion(pdf_id)
        
        # extract key findings from each conclusion
        findings = []
        if conclusion:
            findings_prompt = f"""Extract 2-3 key findings from this conclusion:

                {conclusion[:1500]}

                List each finding as a single sentence."""

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": findings_prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            findings = [f.strip() for f in response.choices[0].message.content.split("\n") if f.strip()]
        
        paper_summaries.append(PaperSummary(
            pdf_id=pdf_id,
            abstract=abstract[:500] if abstract else None,
            methodology=methodology.get("summary"),
            key_findings=findings[:3],
            limitations=None,
        ))
    
    # identify themes
    all_abstracts = "\n\n".join(
        f"Paper {s.pdf_id}: {s.abstract}" 
        for s in paper_summaries 
        if s.abstract
    )
    
    themes_prompt = f"""Identify 3-5 major themes across these paper abstracts:

        {all_abstracts[:4000]}

        For each theme, provide:
        1. Theme name (2-4 words)
        2. Brief description (1 sentence)
        3. Which papers address this theme

        Format:
        THEME: [name]
        DESCRIPTION: [description]
        PAPERS: [comma-separated list]"""

    themes_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": themes_prompt}],
        max_tokens=600,
        temperature=0.4,
    )
    
    # parse themes
    themes_text = themes_response.choices[0].message.content
    themes = []
    
    theme_blocks = re.split(r'\n(?=THEME:)', themes_text)
    for block in theme_blocks:
        if "THEME:" in block:
            name_match = re.search(r'THEME:\s*(.+)', block)
            desc_match = re.search(r'DESCRIPTION:\s*(.+)', block)
            papers_match = re.search(r'PAPERS:\s*(.+)', block)
            
            themes.append({
                "name": name_match.group(1).strip() if name_match else "Unknown Theme",
                "description": desc_match.group(1).strip() if desc_match else "",
                "papers": papers_match.group(1).strip() if papers_match else "",
            })
    
    # generate synthesis
    synthesis_result = synthesize_findings(pdf_ids)
    
    # methodology overview
    methodology_texts = []
    for summary in paper_summaries:
        if summary.methodology:
            methodology_texts.append(f"**{summary.pdf_id}**: {summary.methodology}")
    
    methodology_overview = "\n\n".join(methodology_texts) if methodology_texts else "Methodology information not available."
    
    # identify gaps and future directions
    gaps_prompt = f"""Based on these paper summaries, identify research gaps and future directions:

            {chr(10).join(f"- {s.pdf_id}: {s.abstract[:300]}" for s in paper_summaries if s.abstract)}

            Provide:
            1. 2-3 research gaps identified across these papers
            2. 2-3 suggestions for future research directions
            3. Any methodological improvements that could be made

            Be specific and actionable."""

    gaps_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": gaps_prompt}],
        max_tokens=400,
        temperature=0.4,
    )
    
    gaps_and_future = gaps_response.choices[0].message.content.strip()
    
    # generate title if not provided
    if not title:
        title_prompt = f"""Generate a concise literature review title for papers covering these themes: {', '.join(t['name'] for t in themes[:3])}

            The title should be academic in style, 5-10 words."""
        
        title_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=50,
            temperature=0.5,
        )
        title = title_response.choices[0].message.content.strip().strip('"')
    
    # generate references list
    references = [f"[{i+1}] {pdf_id}" for i, pdf_id in enumerate(pdf_ids)]
    
    return LiteratureReviewReport(
        title=title,
        papers=paper_summaries,
        themes=themes,
        synthesis=synthesis_result.synthesis,
        methodology_overview=methodology_overview,
        gaps_and_future_work=gaps_and_future,
        references=references,
        format=format,
    )

def analyze_literature(
    pdf_ids: List[str],
    analysis_type: str = "synthesis",
    focus_question: Optional[str] = None,
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    Main entry point for literature analysis.
    
    Args:
        pdf_ids: Papers to analyze
        analysis_type: Type of analysis ("compare", "synthesis", "review")
        focus_question: Optional question to focus the analysis
        output_format: "json" or "markdown"
        
    Returns:
        Analysis results as a dictionary
    """
    if analysis_type == "compare":
        result = compare_papers(pdf_ids)
        return {
            "type": "comparison",
            "pdf_ids": result.pdf_ids,
            "similarities": result.similarities,
            "differences": result.differences,
            "key_themes": result.key_themes,
            "methodology_comparison": result.methodology_comparison,
        }
    
    elif analysis_type == "synthesis":
        result = synthesize_findings(pdf_ids, focus_question)
        return {
            "type": "synthesis",
            "synthesis": result.synthesis,
            "citations": result.citations,
            "methodology_comparison": result.methodology_comparison,
            "findings_comparison": result.findings_comparison,
            "papers_analyzed": result.papers_analyzed,
            "confidence": result.confidence,
        }
    else:
        raise ValueError(f"Unknown analysis type: {analysis_type}")