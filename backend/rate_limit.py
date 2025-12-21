import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 20
    requests_per_hour: int = 100
    burst_limit: int = 5

class RateLimiter:
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._minute_buckets: dict[str, list[float]] = defaultdict(list)
        self._hour_buckets: dict[str, list[float]] = defaultdict(list)
    
    # remove requests outside the time window
    def _clean_old_requests(self, bucket: list, window_seconds: int) -> list:
        now = time.time()
        return [t for t in bucket if now - t < window_seconds]
    
    # check if client is within rate limits
    def check_rate_limit(self, client_id: str) -> dict:
        now = time.time()
        
        # clean old requests
        self._minute_buckets[client_id] = self._clean_old_requests(
            self._minute_buckets[client_id], 60
        )
        self._hour_buckets[client_id] = self._clean_old_requests(
            self._hour_buckets[client_id], 3600
        )
        
        minute_count = len(self._minute_buckets[client_id])
        hour_count = len(self._hour_buckets[client_id])
        
        # check minute limit
        if minute_count >= self.config.requests_per_minute:
            oldest = min(self._minute_buckets[client_id])
            retry_after = 60 - (now - oldest)
            return {
                "allowed": False,
                "retry_after": max(1, int(retry_after)),
                "reason": f"Rate limit exceeded: {self.config.requests_per_minute} requests per minute",
            }
        
        # check hour limit
        if hour_count >= self.config.requests_per_hour:
            oldest = min(self._hour_buckets[client_id])
            retry_after = 3600 - (now - oldest)
            return {
                "allowed": False,
                "retry_after": max(1, int(retry_after)),
                "reason": f"Rate limit exceeded: {self.config.requests_per_hour} requests per hour",
            }
        
        # check burst limit (requests in last 5 seconds)
        recent = [t for t in self._minute_buckets[client_id] if now - t < 5]
        if len(recent) >= self.config.burst_limit:
            return {
                "allowed": False,
                "retry_after": 5,
                "reason": "Too many requests in quick succession. Please slow down.",
            }
        
        return {"allowed": True, "retry_after": 0, "reason": None}
    
    # record a request for rate limiting
    def record_request(self, client_id: str):
        now = time.time()
        self._minute_buckets[client_id].append(now)
        self._hour_buckets[client_id].append(now)
    
    # get remaining requests for client
    def get_remaining(self, client_id: str) -> dict:
        self._minute_buckets[client_id] = self._clean_old_requests(
            self._minute_buckets[client_id], 60
        )
        self._hour_buckets[client_id] = self._clean_old_requests(
            self._hour_buckets[client_id], 3600
        )
        
        return {
            "minute_remaining": self.config.requests_per_minute - len(self._minute_buckets[client_id]),
            "hour_remaining": self.config.requests_per_hour - len(self._hour_buckets[client_id]),
        }