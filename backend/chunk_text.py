from pathlib import Path
from typing import List

# loads extracted text from a given file path
def load_extracted_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Could not find the correct path")

    return path.read_text(encoding="utf-8")

# simple tokenizer
def simple_tokenize(text: str) -> List[str]:
    return text.split()

# splits a list of tokens into overlapping chunks
def chunk_tokens(tokens: List[str], chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    
    chunks: List[str] = []