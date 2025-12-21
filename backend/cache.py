import hashlib
import time
from typing import Optional, List
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime

class CacheEntry:
    embedding: List[float]
    created_at: float = field(default_factory=time.time)
    hits: int = 0