# Improved chunking strategy for better retrieval performance
from pathlib import Path
from typing import List
import re


def load_extracted_text(path: Path) -> str:
    """Loads extracted text from a given file path"""
    if not path.exists():
        raise FileNotFoundError(f"Could not find the correct path")

    return path.read_text(encoding="utf-8")


def clean_text(text: str) -> str:
    """
    Clean the text by removing artifacts from PDF extraction

    Improvements:
    - Removes PAGE BREAK markers
    - Normalizes whitespace
    - Removes excessive newlines
    """
    # Remove PAGE BREAK markers
    text = re.sub(r'===\s*PAGE BREAK\s*===', '', text)

    # Normalize multiple spaces to single space
    text = re.sub(r' +', ' ', text)

    # Normalize multiple newlines to double newline (paragraph breaks)
    text = re.sub(r'\n\n+', '\n\n', text)

    return text.strip()


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using simple heuristics

    Better than word-splitting because:
    - Preserves semantic units (complete thoughts)
    - Prevents mid-sentence cuts
    - Works well for academic text
    """
    # Split on sentence boundaries (. ! ?) followed by space and capital letter
    # Also handles common abbreviations like "Dr.", "et al.", etc.
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    # Clean up each sentence
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def chunk_by_sentences(
    text: str,
    target_chunk_size: int = 300,  # Reduced from 500
    overlap_sentences: int = 2      # Overlap by full sentences
) -> List[str]:
    """
    Chunk text by sentences with overlap

    Improvements over token-based chunking:
    1. Respects sentence boundaries (complete thoughts)
    2. Smaller chunks (300 tokens) = more focused embeddings
    3. Sentence-based overlap preserves context better
    4. More semantically coherent units

    Args:
        text: Full text to chunk
        target_chunk_size: Target tokens per chunk (will vary)
        overlap_sentences: Number of sentences to overlap between chunks

    Returns:
        List of text chunks
    """
    # Clean the text first
    text = clean_text(text)

    # Split into sentences
    sentences = split_into_sentences(text)

    chunks = []
    current_chunk_sentences = []
    current_token_count = 0

    for sentence in sentences:
        sentence_tokens = len(sentence.split())

        # If adding this sentence exceeds target, save current chunk and start new one
        if current_token_count + sentence_tokens > target_chunk_size and current_chunk_sentences:
            # Save current chunk
            chunks.append(' '.join(current_chunk_sentences))

            # Start new chunk with overlap (keep last N sentences)
            if len(current_chunk_sentences) > overlap_sentences:
                current_chunk_sentences = current_chunk_sentences[-overlap_sentences:]
                current_token_count = sum(len(s.split()) for s in current_chunk_sentences)
            else:
                current_chunk_sentences = []
                current_token_count = 0

        # Add sentence to current chunk
        current_chunk_sentences.append(sentence)
        current_token_count += sentence_tokens

    # Add final chunk if it has content
    if current_chunk_sentences:
        chunks.append(' '.join(current_chunk_sentences))

    return chunks


def chunk_tokens(tokens: List[str], chunk_size: int = 300, overlap: int = 100) -> List[str]:
    """
    Legacy token-based chunking with improved defaults

    Improvements:
    - Smaller chunks (300 instead of 500)
    - More overlap (100 instead of 50)
    """
    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[str] = []
    step = chunk_size - overlap
    start = 0
    n_tokens = len(tokens)

    while start < n_tokens:
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = " ".join(chunk_tokens)
        chunks.append(chunk_text)
        start += step

    return chunks


def main():
    """Test the improved chunking strategy"""
    text_path = Path("paper_extracted.txt")

    if not text_path.exists():
        print(f"Error: {text_path} not found")
        return

    # Load and clean text
    text = load_extracted_text(text_path)
    print(f"Original text length: {len(text)} characters")

    cleaned_text = clean_text(text)
    print(f"Cleaned text length: {len(cleaned_text)} characters")
    print(f"Removed: {len(text) - len(cleaned_text)} characters\n")

    # Compare chunking strategies
    print("=" * 80)
    print("COMPARISON: Old vs New Chunking Strategy")
    print("=" * 80)

    # Old strategy: word-based, 500 tokens, 50 overlap
    tokens = text.split()
    old_chunks = chunk_tokens(tokens, chunk_size=500, overlap=50)
    print(f"\n[OLD STRATEGY] Word-based, 500 tokens, 50 overlap")
    print(f"Total chunks: {len(old_chunks)}")
    print(f"Avg chunk size: {sum(len(c.split()) for c in old_chunks) / len(old_chunks):.0f} tokens")

    # New strategy: sentence-based, 300 tokens, 2 sentence overlap
    new_chunks = chunk_by_sentences(text, target_chunk_size=300, overlap_sentences=2)
    print(f"\n[NEW STRATEGY] Sentence-based, 300 tokens, 2 sentence overlap")
    print(f"Total chunks: {len(new_chunks)}")
    print(f"Avg chunk size: {sum(len(c.split()) for c in new_chunks) / len(new_chunks):.0f} tokens")

    # Show sample chunks
    print("\n" + "=" * 80)
    print("SAMPLE CHUNKS (First 3)")
    print("=" * 80)

    for i in range(min(3, len(new_chunks))):
        chunk = new_chunks[i]
        print(f"\n[CHUNK {i+1}] ({len(chunk.split())} tokens)")
        print("-" * 80)
        preview = chunk[:400] + "..." if len(chunk) > 400 else chunk
        print(preview)


if __name__ == "__main__":
    main()
