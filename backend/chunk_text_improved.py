# Advanced chunking strategy for research paper RAG
# Addresses: section awareness, metadata, hierarchical chunks, better splitting

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class Chunk:
    """Rich chunk with metadata for better retrieval and citation"""
    text: str
    metadata: Dict = field(default_factory=dict)
    
    # Metadata includes:
    # - document_id: str
    # - section: str (e.g., "Abstract", "Methods")
    # - page_numbers: List[int]
    # - chunk_type: str ("section_summary", "paragraph", "full_section")
    # - parent_chunk_id: Optional[str] (for hierarchical retrieval)
    # - token_count: int


# =============================================================================
# SECTION DETECTION - Critical for research papers
# =============================================================================

# Common section headers in research papers (case-insensitive matching)
SECTION_PATTERNS = [
    # Standard IMRaD sections
    (r'^\s*abstract\s*$', 'Abstract'),
    (r'^\s*introduction\s*$', 'Introduction'),
    (r'^\s*background\s*$', 'Background'),
    (r'^\s*related\s+work\s*$', 'Related Work'),
    (r'^\s*literature\s+review\s*$', 'Literature Review'),
    (r'^\s*methods?\s*$', 'Methods'),
    (r'^\s*methodology\s*$', 'Methods'),
    (r'^\s*materials?\s+and\s+methods?\s*$', 'Methods'),
    (r'^\s*experimental?\s+(?:setup|design|methods?)?\s*$', 'Methods'),
    (r'^\s*results?\s*$', 'Results'),
    (r'^\s*findings?\s*$', 'Results'),
    (r'^\s*results?\s+and\s+discussion\s*$', 'Results and Discussion'),
    (r'^\s*discussion\s*$', 'Discussion'),
    (r'^\s*analysis\s*$', 'Analysis'),
    (r'^\s*conclusions?\s*$', 'Conclusion'),
    (r'^\s*summary\s*$', 'Conclusion'),
    (r'^\s*limitations?\s*$', 'Limitations'),
    (r'^\s*future\s+work\s*$', 'Future Work'),
    (r'^\s*acknowledg[e]?ments?\s*$', 'Acknowledgements'),
    (r'^\s*references?\s*$', 'References'),
    (r'^\s*bibliography\s*$', 'References'),
    (r'^\s*appendix\s*', 'Appendix'),
    
    # Numbered sections (e.g., "1. Introduction", "2 Methods")
    (r'^\s*\d+\.?\s*introduction\s*$', 'Introduction'),
    (r'^\s*\d+\.?\s*background\s*$', 'Background'),
    (r'^\s*\d+\.?\s*related\s+work\s*$', 'Related Work'),
    (r'^\s*\d+\.?\s*methods?\s*$', 'Methods'),
    (r'^\s*\d+\.?\s*results?\s*$', 'Results'),
    (r'^\s*\d+\.?\s*discussion\s*$', 'Discussion'),
    (r'^\s*\d+\.?\s*conclusions?\s*$', 'Conclusion'),

    # ALL-CAPS headers (common in some journals)
    (r'^\s*ABSTRACT\s*$', 'Abstract'),
    (r'^\s*INTRODUCTION\s*$', 'Introduction'),
    (r'^\s*METHODS?\s*$', 'Methods'),
    (r'^\s*RESULTS?\s*$', 'Results'),
    (r'^\s*DISCUSSION\s*$', 'Discussion'),
    (r'^\s*CONCLUSIONS?\s*$', 'Conclusion'),

    # Roman numeral sections (e.g., "I. Introduction", "II. Methods")
    (r'^\s*[IVX]+\.?\s*introduction\s*$', 'Introduction'),
    (r'^\s*[IVX]+\.?\s*methods?\s*$', 'Methods'),
    (r'^\s*[IVX]+\.?\s*results?\s*$', 'Results'),
    (r'^\s*[IVX]+\.?\s*discussion\s*$', 'Discussion'),
    (r'^\s*[IVX]+\.?\s*conclusions?\s*$', 'Conclusion'),

    # Subsections (optional - helps with granularity)
    (r'^\s*\d+\.\d+\.?\s+\w+', 'Subsection'),
]

# Sections to skip or handle specially (they hurt retrieval)
SKIP_SECTIONS = {'References', 'Bibliography', 'Acknowledgements', 'Appendix'}


def detect_section(line: str) -> Optional[str]:
    """Detect if a line is a section header"""
    line_clean = line.strip()
    
    # Skip very long lines (not headers)
    if len(line_clean) > 100:
        return None
    
    # Skip lines that are mostly numbers/symbols
    alpha_ratio = sum(c.isalpha() for c in line_clean) / max(len(line_clean), 1)
    if alpha_ratio < 0.5:
        return None
    
    for pattern, section_name in SECTION_PATTERNS:
        if re.match(pattern, line_clean, re.IGNORECASE):
            return section_name
    
    return None

# detect subsection headers like '2.1 Data Collection'
def detect_subsection(line: str) -> Optional[str]:
    line_clean = line.strip()
    
    # Numbered subsections: 2.1, 3.2.1, etc.
    if re.match(r'^\d+\.\d+\.?\s+\w+', line_clean):
        return line_clean
    
    # Letter subsections: A., B., etc.
    if re.match(r'^[A-Z]\.\s+\w+', line_clean):
        return line_clean
    
    return None


def split_into_sections(text: str) -> List[Tuple[str, str]]:
    """
    Split document into sections with their headers
    
    Returns: List of (section_name, section_text) tuples
    """
    lines = text.split('\n')
    sections = []
    current_section = "Preamble"  # Content before first detected section
    current_content = []
    
    for line in lines:
        detected = detect_section(line)
        
        if detected:
            # Save previous section if it has content
            if current_content:
                content_text = '\n'.join(current_content).strip()
                if content_text:
                    sections.append((current_section, content_text))
            
            # Start new section
            current_section = detected
            current_content = []
        else:
            current_content.append(line)
    
    # Don't forget the last section
    if current_content:
        content_text = '\n'.join(current_content).strip()
        if content_text:
            sections.append((current_section, content_text))
    
    return sections


# =============================================================================
# IMPROVED TEXT CLEANING
# =============================================================================

def clean_text(text: str) -> str:
    """
    Clean text while preserving structure
    
    More aggressive than before but structure-aware
    """
    # Remove PAGE BREAK markers
    text = re.sub(r'===\s*PAGE BREAK\s*===', '\n\n', text)
    
    # Remove page numbers (common patterns)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    text = re.sub(r'\n\s*Page\s+\d+\s*\n', '\n', text, flags=re.IGNORECASE)
    
    # Remove header/footer artifacts (repeated short lines)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip very short lines that look like headers/footers
        stripped = line.strip()
        if len(stripped) < 5 and not stripped[0:1].isalpha():
            continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)
    
    # Normalize whitespace
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Fix broken words from PDF extraction (hy- phenation)
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    return text.strip()


def clean_section_text(text: str, section_name: str) -> str:
    """Section-specific cleaning"""
    text = clean_text(text)
    
    # For references section, we might want to keep it minimal
    if section_name == 'References':
        # Just return first few references as context
        lines = text.split('\n')
        return '\n'.join(lines[:10]) if len(lines) > 10 else text
    
    return text


# =============================================================================
# IMPROVED SENTENCE SPLITTING
# =============================================================================

# Abbreviations that shouldn't end sentences
ABBREVIATIONS = {
    'dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr',
    'vs', 'etc', 'al', 'fig', 'figs', 'eq', 'eqs',
    'vol', 'vols', 'no', 'nos', 'pp', 'p',
    'inc', 'corp', 'ltd', 'co',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'i.e', 'e.g', 'cf', 'viz', 'approx',
}


def split_into_sentences(text: str) -> List[str]:
    """
    Improved sentence splitting that handles academic text
    
    Handles:
    - Abbreviations (et al., Fig., Dr.)
    - Citations (Smith et al. found...)
    - Decimal numbers (3.14)
    - Parenthetical references
    """
    # Protect abbreviations
    for abbr in ABBREVIATIONS:
        # Match abbreviation followed by period
        pattern = rf'\b({abbr})\.'
        text = re.sub(pattern, rf'\1<PERIOD>', text, flags=re.IGNORECASE)
    
    # Protect decimal numbers
    text = re.sub(r'(\d)\.(\d)', r'\1<DECIMAL>\2', text)
    
    # Protect ellipsis
    text = re.sub(r'\.{3}', '<ELLIPSIS>', text)
    
    # Now split on actual sentence boundaries
    # Sentence ends with . ! ? followed by space and capital letter or newline
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])|(?<=[.!?])\s*\n+', text)
    
    # Restore protected characters
    restored = []
    for sent in sentences:
        sent = sent.replace('<PERIOD>', '.')
        sent = sent.replace('<DECIMAL>', '.')
        sent = sent.replace('<ELLIPSIS>', '...')
        sent = sent.strip()
        if sent:
            restored.append(sent)
    
    return restored


# =============================================================================
# HIERARCHICAL CHUNKING - The key improvement
# =============================================================================

def create_chunks_hierarchical(
    text: str,
    document_id: str = "doc",
    small_chunk_size: int = 400,    # Increased for better context
    large_chunk_size: int = 800,    # For context in generation
    overlap_sentences: int = 3      # More overlap for continuity
) -> List[Chunk]:
    """
    Create hierarchical chunks at multiple granularities
    
    Strategy:
    1. Split into sections (semantic boundaries)
    2. Create section-level chunks (good for broad questions)
    3. Create paragraph-level chunks within sections (good for specific questions)
    4. Link small chunks to their parent section
    
    This allows:
    - Retrieve small chunks for precision
    - Expand to parent chunk for context during generation
    """
    all_chunks = []
    sections = split_into_sections(text)
    
    for section_name, section_text in sections:
        # Skip sections that hurt retrieval
        if section_name in SKIP_SECTIONS:
            continue
        
        section_text = clean_section_text(section_text, section_name)
        section_words = section_text.split()
        section_word_count = len(section_words)

        if not section_text or section_word_count < 20:
            continue
        
        section_id = f"{document_id}_{section_name.lower().replace(' ', '_')}"
        
        # --- LEVEL 1: Section summary chunk ---
        # Good for questions like "what is this paper about?"
        section_chunk = Chunk(
            text=section_text[:2000] if len(section_text) > 2000 else section_text,
            metadata={
                'document_id': document_id,
                'chunk_id': section_id,
                'section': section_name,
                'chunk_type': 'section',
                'token_count': section_word_count,
            }
        )
        all_chunks.append(section_chunk)
        
        # --- LEVEL 2: Paragraph/sentence-based chunks ---
        # Good for specific questions
        sentences = split_into_sentences(section_text)
        
        current_chunk_sentences = []
        current_tokens = 0
        chunk_index = 0
        
        for sent in sentences:
            sent_words = sent.split()
            sent_tokens = len(sent_words)
            
            if current_tokens + sent_tokens > small_chunk_size and current_chunk_sentences:
                # Create chunk
                chunk_text = ' '.join(current_chunk_sentences)
                chunk_words = chunk_text.split()
                chunk_word_count = len(chunk_words)
                chunk = Chunk(
                    text=chunk_text,
                    metadata={
                        'document_id': document_id,
                        'chunk_id': f"{section_id}_chunk_{chunk_index}",
                        'section': section_name,
                        'chunk_type': 'paragraph',
                        'parent_chunk_id': section_id,  # Link to section
                        'token_count': len(chunk_text.split()),
                    }
                )
                all_chunks.append(chunk)
                chunk_index += 1
                
                # Overlap: keep last N sentences
                if len(current_chunk_sentences) > overlap_sentences:
                    current_chunk_sentences = current_chunk_sentences[-overlap_sentences:]
                    current_tokens = sum(len(s.split()) for s in current_chunk_sentences)
                else:
                    current_chunk_sentences = []
                    current_tokens = 0
            
            current_chunk_sentences.append(sent)
            current_tokens += sent_tokens
        
        # Final chunk in section
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            chunk = Chunk(
                text=chunk_text,
                metadata={
                    'document_id': document_id,
                    'chunk_id': f"{section_id}_chunk_{chunk_index}",
                    'section': section_name,
                    'chunk_type': 'paragraph',
                    'parent_chunk_id': section_id,
                    'token_count': len(chunk_text.split()),
                }
            )
            all_chunks.append(chunk)
    
    return all_chunks


# =============================================================================
# SEMANTIC CHUNKING (Alternative strategy)
# =============================================================================

def chunk_by_paragraphs(
    text: str,
    document_id: str = "doc",
    min_chunk_size: int = 100,
    max_chunk_size: int = 400,
) -> List[Chunk]:
    """
    Chunk by natural paragraph boundaries
    
    Paragraphs are natural semantic units in academic writing.
    Merge small paragraphs, split large ones.
    """
    sections = split_into_sections(text)
    all_chunks = []
    
    for section_name, section_text in sections:
        if section_name in SKIP_SECTIONS:
            continue
        
        section_text = clean_section_text(section_text, section_name)
        
        # Split into paragraphs (double newline)
        paragraphs = re.split(r'\n\s*\n', section_text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        section_id = f"{document_id}_{section_name.lower().replace(' ', '_')}"
        
        for para in paragraphs:
            para_words = para.split()
            para_tokens = len(para_words)
            
            # If paragraph alone exceeds max, split it by sentences
            if para_tokens > max_chunk_size:
                # Save current chunk first
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunk_word_count = len(chunk_text.split())
                    all_chunks.append(Chunk(
                        text=chunk_text,
                        metadata={
                            'document_id': document_id,
                            'chunk_id': f"{section_id}_p{chunk_index}",
                            'section': section_name,
                            'chunk_type': 'paragraph',
                            'token_count': chunk_word_count,
                        }
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0
                
                # Split large paragraph by sentences
                sentences = split_into_sentences(para)
                sent_chunk = []
                sent_tokens = 0
                
                for sent in sentences:
                    st = len(sent.split())
                    if sent_tokens + st > max_chunk_size and sent_chunk:
                        chunk_text = ' '.join(sent_chunk)
                        all_chunks.append(Chunk(
                            text=chunk_text,
                            metadata={
                                'document_id': document_id,
                                'chunk_id': f"{section_id}_p{chunk_index}",
                                'section': section_name,
                                'chunk_type': 'paragraph',
                                'token_count': len(chunk_text.split()),
                            }
                        ))
                        chunk_index += 1
                        sent_chunk = [sent]
                        sent_tokens = st
                    else:
                        sent_chunk.append(sent)
                        sent_tokens += st
                
                if sent_chunk:
                    chunk_text = ' '.join(sent_chunk)
                    all_chunks.append(Chunk(
                        text=chunk_text,
                        metadata={
                            'document_id': document_id,
                            'chunk_id': f"{section_id}_p{chunk_index}",
                            'section': section_name,
                            'chunk_type': 'paragraph',
                            'token_count': len(chunk_text.split()),
                        }
                    ))
                    chunk_index += 1
                
                continue
            
            # If adding this paragraph exceeds max, save current and start new
            if current_tokens + para_tokens > max_chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                all_chunks.append(Chunk(
                    text=chunk_text,
                    metadata={
                        'document_id': document_id,
                        'chunk_id': f"{section_id}_p{chunk_index}",
                        'section': section_name,
                        'chunk_type': 'paragraph',
                        'token_count': len(chunk_text.split()),
                    }
                ))
                chunk_index += 1
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(para)
            current_tokens += para_tokens
        
        # Final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text.split()) >= min_chunk_size:
                all_chunks.append(Chunk(
                    text=chunk_text,
                    metadata={
                        'document_id': document_id,
                        'chunk_id': f"{section_id}_p{chunk_index}",
                        'section': section_name,
                        'chunk_type': 'paragraph',
                        'token_count': len(chunk_text.split()),
                    }
                ))
    
    return all_chunks

def chunk_recursive(text: str, document_id: str = "doc", max_chunk_size: int = 400, min_chunk_size: int = 50) -> List[Chunk]:
    chunks: List[Chunk] = []
    chunk_index = 0

    sections = split_into_sections(text)
    raw_chunks: List[Chunk] = []

    current_pos = 0

    for section in sections:
        section_title = section.get("title", "")
        section_content = section.get("content", "")

        if not section_content.strip():
            continue

        paragraphs = re.split(r'\n\s*\n', section_content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        pending_chunks: List[str] = []

        for para in paragraphs:
            word_count = len(para.split())

            if word_count <= max_chunk_size:
                pending_chunks.append(para)
            else:
                sentences = split_into_sentences(para)

                current_sentence_group = []
                current_word_count = 0

                for sentence in sentences:
                    sent_word_list = sentence.split()
                    sentence_words = len(sent_word_list)

                    if sentence_words > max_chunk_size:
                        if current_sentence_group:
                            pending_chunks.append(" ".join(current_sentence_group))
                            current_sentence_group = []
                            current_word_count = 0
                        
                        for i in range(0, len(sent_word_list), max_chunk_size):
                            word_chunk = " ".join(sent_word_list[i:i + max_chunk_size])
                            pending_chunks.append(word_chunk)
                    elif current_word_count + sentence_words <= max_chunk_size:
                        current_sentence_group.append(sentence)
                        current_word_count += sentence_words
                    else:
                        if current_sentence_group:
                            pending_chunks.append(" ".join(current_sentence_group))
                        current_sentence_group = [sentence]
                        current_word_count = sentence_words
                
                if current_sentence_group:
                    pending_chunks.append(" ".join(current_sentence_group))
        
        merged_chunks: List[str] = []
        for chunk_text in pending_chunks:
            if not merged_chunks:
                merged_chunks.append(chunk_text)
            elif len(merged_chunks[-1].split()) < min_chunk_size:
                merged_chunks[-1] = merged_chunks[-1] + "\n\n" + chunk_text
            elif len(chunk_text.split()) < min_chunk_size and merged_chunks:
                merged_chunks[-1] = merged_chunks[-1] + "\n\n" + chunk_text
            else:
                merged_chunks.append(chunk_text)

        for chunk_text in merged_chunks:
            word_count = len(chunk_text.split())

            if word_count <= min_chunk_size:
                chunk_type = "merged"
            elif "\n\n" in chunk_text:
                chunk_type = "paragraph"
            else:
                chunk_type = "sentence"
            
            start_char = current_pos
            end_char = start_char + len(chunk_text)
            chunks.append(Chunk(
                chunk_id=f"{document_id}_chunk_{chunk_index}",
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
                word_count=word_count,
                metadata={
                    "section": section_title,
                    "chunk_type": chunk_type,
                    "method": "recursive"
                }
            ))

            chunk_index += 1
            current_pos = end_char
    return chunks

# compare different chunking strategies on the same text
def compare_chunking_strategies(text: str, document_id: str = "test") -> Dict:
    strategies = ["hierarchical", "paragraph", "sentence", "recursive"]
    results = {}
    
    for strategy in strategies:
        try:
            chunks = chunk_document(text, document_id, strategy=strategy)
            
            token_counts = [c.metadata.get('token_count', len(c.text.split())) for c in chunks]
            
            results[strategy] = {
                'num_chunks': len(chunks),
                'avg_tokens': sum(token_counts) / len(token_counts) if token_counts else 0,
                'min_tokens': min(token_counts) if token_counts else 0,
                'max_tokens': max(token_counts) if token_counts else 0,
                'sections_found': len(set(c.metadata.get('section', '') for c in chunks)),
            }
        except Exception as e:
            results[strategy] = {'error': str(e)}
    
    return results



# =============================================================================
# QUERY-AWARE CHUNKING ENHANCEMENT
# =============================================================================

def create_question_focused_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """
    Create additional chunks optimized for common question types
    
    Research papers are often queried for:
    - Methods/methodology
    - Key findings/results
    - Limitations
    - Future work
    - Comparisons to prior work
    
    This creates synthetic chunks that directly answer these.
    """
    enhanced_chunks = list(chunks)
    
    # Group chunks by section
    section_chunks = {}
    for chunk in chunks:
        section = chunk.metadata.get('section', 'Unknown')
        if section not in section_chunks:
            section_chunks[section] = []
        section_chunks[section].append(chunk)
    
    # Create combined "key findings" chunk from Results + Conclusion
    results_text = []
    for section in ['Results', 'Results and Discussion', 'Conclusion', 'Discussion']:
        if section in section_chunks:
            for chunk in section_chunks[section][:2]:  # First 2 chunks
                results_text.append(chunk.text)
    
    if results_text:
        enhanced_chunks.append(Chunk(
            text=' '.join(results_text)[:2000],
            metadata={
                'chunk_id': 'synthetic_key_findings',
                'section': 'Key Findings',
                'chunk_type': 'synthetic',
                'token_count': len(' '.join(results_text).split()),
            }
        ))
    
    # Create "methodology summary" chunk
    if 'Methods' in section_chunks:
        methods_text = ' '.join([c.text for c in section_chunks['Methods'][:2]])
        enhanced_chunks.append(Chunk(
            text=methods_text[:1500],
            metadata={
                'chunk_id': 'synthetic_methods',
                'section': 'Methods Summary',
                'chunk_type': 'synthetic',
                'token_count': len(methods_text.split()),
            }
        ))
    
    return enhanced_chunks


# =============================================================================
# MAIN CHUNKING FUNCTION
# =============================================================================

def chunk_document(
    text: str,
    document_id: str = "doc",
    strategy: str = "hierarchical",  # "hierarchical", "paragraph", or "sentence"
    chunk_size: int = 400,           # Optimal balance: context + focus
    overlap: int = 3,                # More overlap for better continuity
    add_synthetic: bool = True,
) -> List[Chunk]:
    """
    Main entry point for chunking a document
    
    Args:
        text: Full document text
        document_id: Unique identifier for the document
        strategy: Chunking strategy to use
        chunk_size: Target chunk size in tokens
        overlap: Overlap (sentences for sentence strategy, ignored for others)
        add_synthetic: Whether to add synthetic question-focused chunks
    
    Returns:
        List of Chunk objects with text and metadata
    """
    text = clean_text(text)
    
    if strategy == "hierarchical":
        chunks = create_chunks_hierarchical(
            text, 
            document_id=document_id,
            small_chunk_size=chunk_size,
        )
    elif strategy == "paragraph":
        chunks = chunk_by_paragraphs(
            text,
            document_id=document_id,
            max_chunk_size=chunk_size,
        )
    elif strategy == "recursive":
        chunks = chunk_recursive(
            text,
            document_id=document_id,
            max_chunk_size=chunk_size,
        )
    else:  # sentence (your original approach, improved)
        sections = split_into_sections(text)
        chunks = []
        for section_name, section_text in sections:
            if section_name in SKIP_SECTIONS:
                continue
            section_text = clean_section_text(section_text, section_name)
            sentences = split_into_sentences(section_text)
            
            current = []
            current_tokens = 0
            chunk_idx = 0
            
            for sent in sentences:
                st = len(sent.split())
                if current_tokens + st > chunk_size and current:
                    chunks.append(Chunk(
                        text=' '.join(current),
                        metadata={
                            'document_id': document_id,
                            'section': section_name,
                            'chunk_type': 'sentence',
                        }
                    ))
                    chunk_idx += 1
                    current = current[-overlap:] if len(current) > overlap else []
                    current_tokens = sum(len(s.split()) for s in current)
                
                current.append(sent)
                current_tokens += st
            
            if current:
                chunks.append(Chunk(
                    text=' '.join(current),
                    metadata={
                        'document_id': document_id,
                        'section': section_name,
                        'chunk_type': 'sentence',
                    }
                ))
    
    if add_synthetic:
        chunks = create_question_focused_chunks(chunks)
    
    return chunks


# =============================================================================
# UTILITY: Convert chunks to format for vector DB
# =============================================================================

def chunks_to_documents(chunks: List[Chunk]) -> List[Dict]:
    """
    Convert Chunk objects to document dicts for vector DB ingestion
    
    Compatible with Chroma, Pinecone, etc.
    """
    documents = []
    for i, chunk in enumerate(chunks):
        doc = {
            'id': chunk.metadata.get('chunk_id', f'chunk_{i}'),
            'text': chunk.text,
            'metadata': chunk.metadata,
        }
        documents.append(doc)
    return documents
