from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Lock
import traceback
from typing import List, Optional, Dict, Any, Callable
import uuid


@dataclass
class BatchJob:
    job_id: str
    pdf_paths: List[str]
    status: str  # "pending", "running", "completed", "completed_with_errors", "failed"
    progress: str  # "X/Y complete"
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    domain: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert BatchJob to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "pdf_paths": self.pdf_paths,
            "status": self.status,
            "progress": self.progress,
            "results": self.results,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "domain": self.domain,
        }


class BatchJobStore:
    """In-memory store for batch jobs with thread-safe operations."""

    def __init__(self):
        self._lock = Lock()
        self._jobs: Dict[str, BatchJob] = {}

    def create_job(self, pdf_paths: List[Path], domain: Optional[str] = None) -> BatchJob:
        job_id = str(uuid.uuid4())
        job = BatchJob(
            job_id=job_id,
            pdf_paths=[str(p) for p in pdf_paths],
            status="pending",
            progress=f"0/{len(pdf_paths)} complete",
            results=[],
            domain=domain,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in updates.items():
                setattr(job, k, v)
    
    def append_result(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.results.append(result)

    def list_jobs(self) -> List[BatchJob]:
        with self._lock:
            # newest first
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

def process_batch(
    pdf_paths: List[Path],
    ingest_paper: Callable,
    store: BatchJobStore,
    domain: Optional[str] = None,
) -> str:
    """
    Start batch processing of multiple PDFs in a background thread.

    Args:
        pdf_paths: List of paths to PDF files
        ingest_paper: The ingestion function to call for each PDF
        store: BatchJobStore instance to track job progress
        domain: Optional domain for domain-specific processing

    Returns:
        job_id: Unique identifier for tracking the batch job
    """
    job = store.create_job(pdf_paths, domain=domain)

    def _runner() -> None:
        total = len(pdf_paths)
        completed = 0
        any_errors = False

        store.update_job(job.job_id, status="running", progress=f"{completed}/{total} complete")

        for p in pdf_paths:
            pdf_path = Path(p) if isinstance(p, str) else p
            pdf_id = pdf_path.stem  # filename without extension
            start_ts = datetime.now(timezone.utc).isoformat()

            try:
                # Call ingestion with pdf_path, pdf_id, and optional domain
                ingest_paper(
                    pdf_path=pdf_path,
                    pdf_id=pdf_id,
                    clear_existing=False,
                    domain=domain,
                )

                store.append_result(job.job_id, {
                    "pdf_path": str(p),
                    "pdf_id": pdf_id,
                    "status": "success",
                    "error": None,
                    "traceback": None,
                    "started_at": start_ts,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                any_errors = True
                store.append_result(job.job_id, {
                    "pdf_path": str(p),
                    "pdf_id": pdf_id,
                    "status": "error",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "started_at": start_ts,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                })
            finally:
                completed += 1
                store.update_job(job.job_id, progress=f"{completed}/{total} complete")

        final_status = "completed_with_errors" if any_errors else "completed"
        store.update_job(
            job.job_id,
            status=final_status,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    Thread(target=_runner, daemon=True).start()
    return job.job_id


# Create a singleton instance for use across the application
batch_job_store = BatchJobStore()