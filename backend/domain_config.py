from dataclasses import dataclass, field
from typing import List, Dict, Set

@dataclass
class DomainConfig:
    name: str

    section_patterns: List[tuple] = field(default_factory=list)

    skip_sections: Set[str] = field(default_factory=set)

    abbreviations: Set[str] = field(default_factory=set)

    important_keywords: Set[str] = field(default_factory=set)

    min_chunk_size: int = 100
    max_chunk_size: int = 400

    preserve_tables: bool = True
    preserve_equations: bool = False
    preserve_code_blocks: bool = False

    synthetic_sections: List[str] = field(default_factory=list)