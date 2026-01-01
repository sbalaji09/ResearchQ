import hashlib
import re
import time
from typing import Optional, List
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CacheEntry:
    embedding: List[float]
    created_at: float = field(default_factory=time.time)
    hits: int = 0

# LRU cache for embeddings with TTL support
class EmbeddingCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._stats = {"hits": 0, "misses": 0}
    
    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]
    
    # get cached embedding if exists and not expired
    def get(self, text: str) -> Optional[List[float]]:
        key = self._hash_text(text)

        if key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        entry = self._cache[key]

        if time.time() - entry.created_at > self._ttl_seconds:
            del self._cache[key]
            self._stats["misses"] += 1
            return None
        
        self._cache.move_to_end(key)
        entry.hits += 1
        self._stats["hits"] += 1
        
        return entry.embedding

    # cache an embedding
    def set(self, text: str, embedding: List[float]):
        key = self._hash_text(text)

        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        
        self._cache[key] = CacheEntry(embedding=embedding)

    # get from cache or compute and cache
    def get_or_compute(self, text: str, compute_fn) -> List[float]:
        cached = self.get(text)
        if cached is not None:
            return cached
        
        embedding = compute_fn(text)
        self.set(text, embedding)
        return embedding
    
    # clear all cached embeddings
    def clear(self):
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0}
    
    # get cache statistics
    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate: .1%}"
        }

# classify query complexity to route to appropriate model
def detect_query_complexity(query: str) -> str:
    query_lower = query.lower().strip()
    words = query_lower.split()
    word_count = len(words)
    
    simple_patterns = [
        r'^what is\b',
        r'^who is\b',
        r'^when was\b',
        r'^where is\b',
        r'^how many\b',
        r'^yes or no\b',
        r'^true or false\b',
    ]
    
    for pattern in simple_patterns:
        if re.match(pattern, query_lower):
            if word_count < 10:
                return "simple"
    
    complex_indicators = [
        'compare', 'contrast', 'analyze', 'explain why',
        'relationship between', 'implications', 'evaluate',
        'synthesize', 'critically', 'in-depth',
        'step by step', 'comprehensive', 'detailed',
    ]
    
    for indicator in complex_indicators:
        if indicator in query_lower:
            return "complex"
    
    # multi part questions are complex
    if query_lower.count('?') > 1:
        return "complex"
    
    # long questions are complex
    if word_count > 25:
        return "complex"
    
    return "simple"

# get model configuration based on complexity
def get_model_for_complexity(complexity: str) -> dict:
    if complexity == "simple":
        return {
            "model": "gpt-4o-mini",
            "max_tokens": 500,
            "temperature": 0.1,
        }
    else:
        return {
            "model": "gpt-4o-mini",  # Can upgrade to gpt-4o for complex
            "max_tokens": 800,
            "temperature": 0.2,
        }

embedding_cache = EmbeddingCache(max_size=1000, ttl_seconds=3600)