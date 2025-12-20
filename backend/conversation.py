from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import json
from pathlib import Path

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    citations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "citations": self.citations
        }