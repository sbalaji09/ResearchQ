from asyncio import Lock
from dataclasses import dataclass, field
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class BatchJob:
    job_id: str
    pdf_paths: List[str]
    status: str
    progress: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(datetime.timezone.utc).isoformat())
    completed_at: Optional[str] = None

@dataclass
class BatchJobStore:
    def __init__(self):
        self._lock = Lock()
        self._jobs: Dict[str, BatchJob] = {}

    def create_job(self, pdf_paths: List[Path]) -> BatchJob:
        job_id = str(uuid.uuid4())
        job = BatchJob(
            job_id=job_id,
            pdf_paths=[str(p) for p in pdf_paths],
            status="pending",
            progress=f"0/{len(pdf_paths)} complete",
            results=[],
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