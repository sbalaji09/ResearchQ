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

# cluster papers using K-Means algorithm
def cluster_papers_kmeans(
    pdf_ids: List[str],
    n_clusters: int,
) -> List[ClusterResult]:
    paper_embeddings = get_all_paper_embeddings(pdf_ids)
    
    if len(paper_embeddings) < n_clusters:
        raise ValueError(f"Cannot create {n_clusters} clusters from {len(paper_embeddings)} papers")
    
    # build embedding matrix
    X = np.array([pe.embedding for pe in paper_embeddings])
    id_map = {i: pe.pdf_id for i, pe in enumerate(paper_embeddings)}
    
    # run k-means
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10,
    )
    labels = kmeans.fit_predict(X)
    
    # group papers by cluster
    clusters = defaultdict(list)
    for idx, label in enumerate(labels):
        clusters[label].append(id_map[idx])
    
    # build results
    results = []
    for cluster_id, members in clusters.items():
        results.append(ClusterResult(
            cluster_id=cluster_id,
            pdf_ids=members,
            centroid=kmeans.cluster_centers_[cluster_id],
        ))
    
    return results

# cluster papers using hierarchial clustering
def cluster_papers_hierarchical(
    pdf_ids: List[str],
    n_clusters: Optional[int] = None,
    distance_threshold: Optional[float] = 0.5,
) -> List[ClusterResult]:
    paper_embeddings = get_all_paper_embeddings(pdf_ids)
    
    if len(paper_embeddings) < 2:
        raise ValueError("Need at least 2 papers to cluster")
    
    X = np.array([pe.embedding for pe in paper_embeddings])
    id_map = {i: pe.pdf_id for i, pe in enumerate(paper_embeddings)}
    
    # configure clustering
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        distance_threshold=distance_threshold if n_clusters is None else None,
        metric="cosine",
        linkage="average",  # average linkage works well with cosine distance
    )
    labels = clustering.fit_predict(X)
    
    # group papers by clustering
    clusters = defaultdict(list)
    for idx, label in enumerate(labels):
        clusters[label].append(id_map[idx])
    
    results = []
    for cluster_id, members in clusters.items():
        member_indices = [i for i, pid in id_map.items() if pid in members]
        centroid = X[member_indices].mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        
        results.append(ClusterResult(
            cluster_id=cluster_id,
            pdf_ids=members,
            centroid=centroid,
        ))
    
    return results

# cluster papers using DBSCAN (Density-Based Spatial Clustering)
def cluster_papers_dbscan(
    pdf_ids: List[str],
    eps: float = 0.3,
    min_samples: int = 2,
) -> Tuple[List[ClusterResult], List[str]]:
    paper_embeddings = get_all_paper_embeddings(pdf_ids)
    
    if len(paper_embeddings) < min_samples:
        raise ValueError(f"Need at least {min_samples} papers for DBSCAN")
    
    X = np.array([pe.embedding for pe in paper_embeddings])
    id_map = {i: pe.pdf_id for i, pe in enumerate(paper_embeddings)}
    
    clustering = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric="cosine",
    )
    labels = clustering.fit_predict(X)
    
    clusters = defaultdict(list)
    outliers = []
    
    for idx, label in enumerate(labels):
        pdf_id = id_map[idx]
        if label == -1:
            outliers.append(pdf_id)
        else:
            clusters[label].append(pdf_id)
    
    results = []
    for cluster_id, members in clusters.items():
        member_indices = [i for i, pid in id_map.items() if pid in members]
        centroid = X[member_indices].mean(axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        
        results.append(ClusterResult(
            cluster_id=cluster_id,
            pdf_ids=members,
            centroid=centroid,
        ))
    
    return results, outliers

# extract representative topics / keywords from a cluster using TF-IDF (terms that are frequent in this cluster, but distinguish it frmo other documents)
def extract_cluster_topics_tfidf(
    cluster: ClusterResult,
    top_n: int = 5,
) -> List[str]:
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)
    
    cluster_texts = []
    
    for pdf_id in cluster.pdf_ids:
        stats = index.describe_index_stats()
        dummy_vector = [0.0] * stats.dimension
        
        results = index.query(
            vector=dummy_vector,
            top_k=1000,
            include_metadata=True,
            filter={"pdf_id": {"$eq": pdf_id}}
        )
        
        # combine all chunk text
        paper_text = " ".join(
            m.metadata.get("text", "") 
            for m in results.matches 
            if m.metadata
        )
        cluster_texts.append(paper_text)
    
    if not cluster_texts:
        return []
    
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words="english",
        ngram_range=(1, 2),  # Include bigrams like "neural network"
        min_df=1,
        max_df=0.95,
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(cluster_texts)
    except ValueError:
        return []
    
    mean_tfidf = np.array(tfidf_matrix.mean(axis=0)).flatten()
    
    feature_names = vectorizer.get_feature_names_out()
    top_indices = mean_tfidf.argsort()[-top_n:][::-1]
    
    topics = [feature_names[i] for i in top_indices]
    
    return topics

# use GPT to generate a summary of what theme connects papers in a cluster
def extract_cluster_topics_llm(
    cluster: ClusterResult,
    max_papers: int = 5,
) -> str:
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)
    
    # collect abstracts / intros from papers
    paper_summaries = []
    
    for pdf_id in cluster.pdf_ids[:max_papers]:
        stats = index.describe_index_stats()
        dummy_vector = [0.0] * stats.dimension
        
        results = index.query(
            vector=dummy_vector,
            top_k=100,
            include_metadata=True,
            filter={"pdf_id": {"$eq": pdf_id}}
        )
        
        summary_text = ""
        for match in results.matches:
            section = match.metadata.get("section", "").lower()
            if "abstract" in section or "introduction" in section:
                summary_text = match.metadata.get("text", "")[:500]
                break
        
        if summary_text:
            paper_summaries.append(f"Paper '{pdf_id}': {summary_text}")
    
    if not paper_summaries:
        return "Unable to determine cluster theme - no text found."
    
    prompt = f"""Analyze these paper excerpts and identify the common theme or topic that connects them.

        Papers in this cluster:
        {chr(10).join(paper_summaries)}

        Provide a concise 1-2 sentence summary of the unifying theme. Focus on:
        - The main research area/domain
        - Common methodologies or approaches
        - Shared problems being addressed

        Theme:"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  # Use a cheaper model for this task
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3,
    )
    
    return response.choices[0].message.content.strip()

# find papers most similar to a given paper by using cosine similarity
def find_similar_papers(
    pdf_id: str,
    top_k: int = 5,
    exclude_self: bool = True,
) -> List[SimilarPaper]:
    query_embedding = get_paper_embedding(pdf_id)
    if query_embedding is None:
        raise ValueError(f"Paper '{pdf_id}' not found in index")
    
    all_pdf_ids = get_all_pdf_ids()
    if exclude_self and pdf_id in all_pdf_ids:
        all_pdf_ids.remove(pdf_id)
    
    if not all_pdf_ids:
        return []
    
    all_embeddings = get_all_paper_embeddings(all_pdf_ids)
    
    query_vec = query_embedding.embedding.reshape(1, -1)
    other_vecs = np.array([pe.embedding for pe in all_embeddings])
    
    similarities = cosine_similarity(query_vec, other_vecs)[0]
    
    # create results
    results = []
    for i, pe in enumerate(all_embeddings):
        results.append(SimilarPaper(
            pdf_id=pe.pdf_id,
            similarity_score=float(similarities[i]),
        ))
    
    # sort by similarity and return top k
    results.sort(key=lambda x: x.similarity_score, reverse=True)
    
    return results[:top_k]
