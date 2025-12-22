import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# represents a paper's aggregated embedding
@dataclass
class PaperEmbedding:
    pdf_id: str
    embedding: np.ndarray
    chunk_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

# result of clustering operation
@dataclass
class ClusterResult:
    cluster_id: int
    pdf_ids: List[str]
    centroid: Optional[np.ndarray] = None
    topics: List[str] = field(default_factory=list)
    summary: Optional[str] = None

# paper similar to the query paper
@dataclass
class SimilarPaper:
    pdf_id: str
    similarity_score: float
    shared_topics: List[str] = field(default_factory=list)

# section weights for computing paper embeddings
SECTION_WEIGHTS = {
    "abstract": 2.0,
    "introduction": 1.5,
    "conclusion": 2.0,
    "results": 1.3,
    "discussion": 1.2,
    "methods": 1.0,
    "methodology": 1.0,
    "related work": 0.8,
    "background": 0.8,
    "references": 0.3,  # Usually not very informative
    "acknowledgments": 0.1,
    "appendix": 0.5,
}

# get the weight for a section based on its name
def get_section_weight(section_name: str) -> float:
    section_lower = section_name.lower().strip()
    
    for key, weight in SECTION_WEIGHTS.items():
        if key in section_lower:
            return weight
    
    return 1.0