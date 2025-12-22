import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from threading import Lock

from literature_review import get_abstract


@dataclass
class PaperMetadata:
    pdf_id: str
    filename: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    domain: Optional[str] = None
    upload_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    chunk_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperMetadata":
        return cls(**data)


class PaperStore:
    """
    JSON-based storage for paper metadata.
    Stores paper-level information that doesn't fit in Pinecone.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path(__file__).parent / "data" / "papers_metadata.json"

        self._storage_path = storage_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._papers: Dict[str, PaperMetadata] = {}
        self._load()

    def _load(self) -> None:
        """Load papers from JSON file."""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r") as f:
                    data = json.load(f)
                    self._papers = {
                        pdf_id: PaperMetadata.from_dict(meta)
                        for pdf_id, meta in data.items()
                    }
            except (json.JSONDecodeError, KeyError):
                self._papers = {}

    def _save(self) -> None:
        """Save papers to JSON file."""
        with open(self._storage_path, "w") as f:
            data = {pdf_id: meta.to_dict() for pdf_id, meta in self._papers.items()}
            json.dump(data, f, indent=2)

    def add_paper(
        self,
        pdf_id: str,
        filename: str,
        domain: Optional[str] = None,
        chunk_count: int = 0,
    ) -> PaperMetadata:
        """Add a new paper to the store."""
        with self._lock:
            # Try to extract abstract from Pinecone chunks
            abstract = None
            try:
                abstract = get_abstract(pdf_id)
                if abstract:
                    abstract = abstract[:1000]  # Truncate to reasonable length
            except Exception:
                pass

            # Extract title from filename
            title = filename.replace(".pdf", "").replace("_", " ")

            metadata = PaperMetadata(
                pdf_id=pdf_id,
                filename=filename,
                title=title,
                abstract=abstract,
                domain=domain,
                chunk_count=chunk_count,
            )

            self._papers[pdf_id] = metadata
            self._save()
            return metadata

    def get_paper(self, pdf_id: str) -> Optional[PaperMetadata]:
        """Get paper metadata by ID."""
        with self._lock:
            return self._papers.get(pdf_id)

    def update_paper(self, pdf_id: str, **updates) -> Optional[PaperMetadata]:
        """Update paper metadata."""
        with self._lock:
            if pdf_id not in self._papers:
                return None

            paper = self._papers[pdf_id]
            for key, value in updates.items():
                if hasattr(paper, key):
                    setattr(paper, key, value)

            self._save()
            return paper

    def delete_paper(self, pdf_id: str) -> bool:
        """Delete paper from store."""
        with self._lock:
            if pdf_id in self._papers:
                del self._papers[pdf_id]
                self._save()
                return True
            return False

    def list_papers(self) -> List[PaperMetadata]:
        """List all papers."""
        with self._lock:
            return list(self._papers.values())

    def get_papers_by_domain(self, domain: str) -> List[PaperMetadata]:
        """Get all papers in a specific domain."""
        with self._lock:
            return [p for p in self._papers.values() if p.domain == domain]

    def clear(self) -> None:
        """Clear all papers."""
        with self._lock:
            self._papers = {}
            self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored papers."""
        with self._lock:
            domains = {}
            for paper in self._papers.values():
                domain = paper.domain or "unknown"
                domains[domain] = domains.get(domain, 0) + 1

            return {
                "total_papers": len(self._papers),
                "papers_by_domain": domains,
            }


# Singleton instance
paper_store = PaperStore()
