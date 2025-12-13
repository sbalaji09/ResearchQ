from pathlib import Path
from typing import List

# loads extracted text from a given file path
def load_extracted_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Could not find the correct path")

    return path.read_text(encoding="utf-8")

