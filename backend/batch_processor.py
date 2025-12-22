from dataclasses import dataclass
import datetime
from typing import List


@dataclass
class BatchJob:
    job_id: str
    pdf_paths: List[str]
    status: str
    progress: str
    results: str
    created_at: datetime
    completed_at: datetime

