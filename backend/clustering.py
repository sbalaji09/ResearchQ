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

# generate a single embedding vector representing an entire paper
def get_paper_embedding(pdf_id: str) -> Optional[PaperEmbedding]:
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)
    
    # get the dimension of the index
    stats = index.describe_index_stats()
    dimension = stats.dimension
    
    # dummy query vector
    dummy_vector = [0.0] * dimension
    
    # get all chunks for this paper
    results = index.query(
        vector=dummy_vector,
        top_k=10000,  # Get all chunks (adjust if you have more)
        include_values=True,
        include_metadata=True,
        filter={"pdf_id": {"$eq": pdf_id}}
    )
    
    if not results.matches:
        print(f"No chunks found for pdf_id: {pdf_id}")
        return None
    
    # collect embeddings with weights
    embeddings = []
    weights = []
    total_tokens = 0
    
    for match in results.matches:
        embedding = np.array(match.values)
        metadata = match.metadata or {}
        
        # get section weight
        section = metadata.get("section", "unknown")
        section_weight = get_section_weight(section)
        
        # get token count weight
        token_count = metadata.get("token_count", 200)
        token_weight = min(token_count / 200, 2.0)  # Cap at 2x
        
        # combine weights
        combined_weight = section_weight * token_weight
        
        embeddings.append(embedding)
        weights.append(combined_weight)
        total_tokens += token_count
    
    # compute weighted average
    embeddings_array = np.array(embeddings)
    weights_array = np.array(weights)
    
    # normalize weights
    weights_normalized = weights_array / weights_array.sum()
    
    paper_embedding = np.average(embeddings_array, axis=0, weights=weights_normalized)
    
    paper_embedding = paper_embedding / np.linalg.norm(paper_embedding)
    
    return PaperEmbedding(
        pdf_id=pdf_id,
        embedding=paper_embedding,
        chunk_count=len(embeddings),
        metadata={
            "total_tokens": total_tokens,
            "sections": list(set(m.metadata.get("section", "unknown") for m in results.matches))
        }
    )

# get embeddings for multiple papers
def get_all_paper_embeddings(pdf_ids: Optional[List[str]] = None) -> List[PaperEmbedding]:
    if pdf_ids is None:
        # get all unique pdf_ids from the index
        pdf_ids = get_all_pdf_ids()
    
    embeddings = []
    for pdf_id in pdf_ids:
        paper_emb = get_paper_embedding(pdf_id)
        if paper_emb is not None:
            embeddings.append(paper_emb)
        else:
            print(f"Warning: Could not get embedding for {pdf_id}")
    
    return embeddings

# get all unique pdf_ids from the Pinecone index
def get_all_pdf_ids() -> List[str]:
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)
    
    stats = index.describe_index_stats()
    dimension = stats.dimension

    dummy_vector = [0.0] * dimension
    
    results = index.query(
        vector=dummy_vector,
        top_k=10000,
        include_metadata=True,
    )
    
    # extract unique pdf_ids
    pdf_ids = set()
    for match in results.matches:
        if match.metadata and "pdf_id" in match.metadata:
            pdf_ids.add(match.metadata["pdf_id"])
    
    return list(pdf_ids)
