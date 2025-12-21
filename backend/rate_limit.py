import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 20
    requests_per_hour: int = 100
    burst_limit: int = 5