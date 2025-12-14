# Advanced retrieval strategies for better RAG performance
# Use alongside improved_chunking.py

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass
class RetrievalResult:
    """Retrieved chunk with scores"""
    chunk_id: str
    text: str
    metadata: Dict
    semantic_score: float
    keyword_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0


# =============================================================================
# 1. QUERY EXPANSION - Improve recall by searching for related terms
# =============================================================================

def expand_query(query: str) -> List[str]:
    """
    Generate query variations to improve recall
    
    Techniques:
    - Acronym expansion
    - Synonym addition
    - Question reformulation
    """
    queries = [query]
    
    # Common academic acronyms
    acronyms = {
        'ML': 'machine learning',
        'DL': 'deep learning',
        'NLP': 'natural language processing',
        'CV': 'computer vision',
        'RL': 'reinforcement learning',
        'CNN': 'convolutional neural network',
        'RNN': 'recurrent neural network',
        'LSTM': 'long short-term memory',
        'GAN': 'generative adversarial network',
        'LLM': 'large language model',
        'RAG': 'retrieval augmented generation',
        'QA': 'question answering',
        'NER': 'named entity recognition',
        'PCA': 'principal component analysis',
        'SVM': 'support vector machine',
        'API': 'application programming interface',
        'GPU': 'graphics processing unit',
        'CPU': 'central processing unit',
    }
    
    # Expand acronyms in query
    query_upper = query.upper()
    for acronym, expansion in acronyms.items():
        if acronym in query_upper:
            expanded = re.sub(acronym, expansion, query, flags=re.IGNORECASE)
            queries.append(expanded)
    
    # Add question reformulations
    question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who']
    query_lower = query.lower()
    
    if any(query_lower.startswith(w) for w in question_words):
        # Convert question to statement-like query
        # "What methods did they use?" -> "methods used"
        simplified = re.sub(r'^(what|how|why|when|where|which|who)\s+(is|are|was|were|did|do|does)?\s*', '', query_lower)
        simplified = re.sub(r'\?$', '', simplified).strip()
        if simplified and simplified != query_lower:
            queries.append(simplified)
    
    # For method questions, add "methodology" and "approach"
    if 'method' in query_lower:
        queries.append(query.replace('method', 'methodology'))
        queries.append(query.replace('method', 'approach'))
    
    # For result questions, add "finding" and "outcome"
    if 'result' in query_lower:
        queries.append(query.replace('result', 'finding'))
        queries.append(query.replace('result', 'outcome'))
    
    return list(set(queries))  # Deduplicate


# =============================================================================
# 2. HYBRID SEARCH - Combine semantic and keyword search
# =============================================================================

def compute_bm25_score(query: str, document: str, k1: float = 1.5, b: float = 0.75) -> float:
    """
    Improved BM25 keyword matching score with proper term weighting

    Args:
        query: Query string
        document: Document text
        k1: Term frequency saturation parameter (default 1.5)
        b: Length normalization parameter (default 0.75)
    """
    from collections import Counter

    query_terms = query.lower().split()
    doc_terms = document.lower().split()

    if not query_terms or not doc_terms:
        return 0.0

    # Term frequency in document
    doc_tf = Counter(doc_terms)
    doc_length = len(doc_terms)
    avg_doc_length = 400  # Approximate average from our chunks

    score = 0.0
    matched_terms = 0

    for term in set(query_terms):
        if term in doc_tf:
            # Term frequency component
            tf = doc_tf[term]

            # Length normalization
            norm_factor = (1 - b) + b * (doc_length / avg_doc_length)

            # BM25 formula
            term_score = (tf * (k1 + 1)) / (tf + k1 * norm_factor)

            # IDF approximation (assume moderate rarity)
            # In full BM25, this would be log((N - df + 0.5) / (df + 0.5))
            # We approximate with a constant boost for matched terms
            idf = 1.5

            score += term_score * idf
            matched_terms += 1

    if matched_terms == 0:
        return 0.0

    # Normalize by query length and add coverage bonus
    coverage = matched_terms / len(set(query_terms))
    normalized_score = (score / len(set(query_terms))) * (0.7 + 0.3 * coverage)

    # Scale to [0, 1] range with sigmoid-like function
    return min(1.0, normalized_score / 3.0)


def hybrid_search(
    query: str,
    chunks: List[Dict],
    embeddings_db,  # Your vector DB client
    alpha: float = 0.7,  # Weight for semantic (0.7 = 70% semantic, 30% keyword)
    top_k: int = 10,
) -> List[RetrievalResult]:
    """
    Combine semantic search with keyword matching
    
    Why this helps:
    - Semantic search finds conceptually similar content
    - Keyword search catches exact matches (names, numbers, acronyms)
    - Combination is more robust than either alone
    """
    # Get semantic results (you'd call your actual vector DB here)
    # semantic_results = embeddings_db.query(query, top_k=top_k * 2)
    
    # For demonstration, assume we have chunks with embeddings
    results = []
    
    for chunk in chunks:
        # In practice, semantic_score comes from vector DB
        # This is a placeholder
        semantic_score = 0.5  # Replace with actual cosine similarity
        
        # Keyword score
        keyword_score = compute_bm25_score(query, chunk['text'])
        
        # Combine scores
        final_score = alpha * semantic_score + (1 - alpha) * keyword_score
        
        results.append(RetrievalResult(
            chunk_id=chunk['id'],
            text=chunk['text'],
            metadata=chunk['metadata'],
            semantic_score=semantic_score,
            keyword_score=keyword_score,
            final_score=final_score,
        ))
    
    # Sort by final score
    results.sort(key=lambda x: x.final_score, reverse=True)
    
    return results[:top_k]


# =============================================================================
# 3. SECTION-AWARE RETRIEVAL - Use metadata for filtering
# =============================================================================

# Map question types to likely sections
QUESTION_SECTION_MAP = {
    'method': ['Methods', 'Methods Summary', 'Methodology'],
    'approach': ['Methods', 'Methods Summary'],
    'technique': ['Methods', 'Methods Summary'],
    'algorithm': ['Methods', 'Methods Summary'],
    'how did': ['Methods', 'Methods Summary'],
    'procedure': ['Methods', 'Methods Summary'],
    
    'result': ['Results', 'Results and Discussion', 'Key Findings'],
    'finding': ['Results', 'Results and Discussion', 'Key Findings'],
    'performance': ['Results', 'Results and Discussion'],
    'accuracy': ['Results', 'Results and Discussion'],
    'outcome': ['Results', 'Results and Discussion', 'Key Findings'],
    
    'limitation': ['Limitations', 'Discussion'],
    'weakness': ['Limitations', 'Discussion'],
    'drawback': ['Limitations', 'Discussion'],
    
    'future': ['Future Work', 'Conclusion', 'Discussion'],
    'next step': ['Future Work', 'Conclusion'],
    
    'background': ['Introduction', 'Background', 'Related Work'],
    'motivation': ['Introduction', 'Background'],
    'prior work': ['Related Work', 'Background'],
    'related': ['Related Work', 'Background'],
    
    'conclusion': ['Conclusion', 'Discussion', 'Key Findings'],
    'summary': ['Conclusion', 'Abstract'],
    'main point': ['Conclusion', 'Abstract'],
    
    'what is': ['Abstract', 'Introduction'],
    'overview': ['Abstract', 'Introduction'],
    'about': ['Abstract', 'Introduction'],
}


def detect_question_type(query: str) -> List[str]:
    """Detect likely sections based on question content"""
    query_lower = query.lower()
    
    relevant_sections = set()
    for keyword, sections in QUESTION_SECTION_MAP.items():
        if keyword in query_lower:
            relevant_sections.update(sections)
    
    return list(relevant_sections) if relevant_sections else []


def section_boosted_retrieval(
    results: List[RetrievalResult],
    query: str,
    boost_factor: float = 1.3,
) -> List[RetrievalResult]:
    """
    Boost scores for chunks from relevant sections
    
    Example: "What methods did they use?" boosts Methods section
    """
    relevant_sections = detect_question_type(query)
    
    if not relevant_sections:
        return results
    
    for result in results:
        chunk_section = result.metadata.get('section', '')
        if chunk_section in relevant_sections:
            result.final_score *= boost_factor
    
    # Re-sort after boosting
    results.sort(key=lambda x: x.final_score, reverse=True)
    
    return results


# =============================================================================
# 4. RE-RANKING - Use a cross-encoder for precise scoring
# =============================================================================

def rerank_with_cross_encoder(
    query: str,
    results: List[RetrievalResult],
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    top_k: int = 5,
) -> List[RetrievalResult]:
    """
    Re-rank results using a cross-encoder model
    
    Why this helps:
    - Bi-encoders (embeddings) encode query and doc separately
    - Cross-encoders see query and doc together = more accurate
    - Expensive, so use on top candidates only
    
    Requires: pip install sentence-transformers
    """
    try:
        from sentence_transformers import CrossEncoder
        
        model = CrossEncoder(model_name)
        
        # Prepare pairs
        pairs = [(query, r.text) for r in results]
        
        # Score all pairs
        scores = model.predict(pairs)
        
        # Update scores
        for i, result in enumerate(results):
            result.rerank_score = float(scores[i])
            result.final_score = result.rerank_score  # Re-ranker overrides
        
        # Sort by rerank score
        results.sort(key=lambda x: x.rerank_score, reverse=True)
        
        return results[:top_k]
    
    except ImportError:
        print("Warning: sentence-transformers not installed, skipping re-ranking")
        return results[:top_k]


# =============================================================================
# 5. CONTEXT EXPANSION - Get parent chunks for more context
# =============================================================================

def expand_to_parent_chunks(
    results: List[RetrievalResult],
    all_chunks: Dict[str, Dict],  # chunk_id -> chunk
    max_context_tokens: int = 1500,
) -> List[Dict]:
    """
    Expand small chunks to their parent sections for more context
    
    Strategy:
    1. Retrieved chunk provides precision
    2. Parent chunk provides surrounding context
    3. LLM gets both for better understanding
    """
    expanded_contexts = []
    seen_parents = set()
    total_tokens = 0
    
    for result in results:
        parent_id = result.metadata.get('parent_chunk_id')
        
        # If chunk has a parent, include it
        if parent_id and parent_id not in seen_parents:
            parent = all_chunks.get(parent_id)
            if parent:
                parent_tokens = len(parent['text'].split())
                if total_tokens + parent_tokens <= max_context_tokens:
                    expanded_contexts.append({
                        'text': parent['text'],
                        'metadata': parent['metadata'],
                        'source': 'parent',
                    })
                    seen_parents.add(parent_id)
                    total_tokens += parent_tokens
        
        # Also include the original chunk if room
        chunk_tokens = len(result.text.split())
        if total_tokens + chunk_tokens <= max_context_tokens:
            expanded_contexts.append({
                'text': result.text,
                'metadata': result.metadata,
                'source': 'retrieved',
            })
            total_tokens += chunk_tokens
    
    return expanded_contexts


# =============================================================================
# 6. MULTI-QUERY RETRIEVAL - Search multiple times, aggregate
# =============================================================================

def multi_query_retrieval(
    query: str,
    embeddings_db,
    top_k: int = 5,
    num_queries: int = 3,
) -> List[RetrievalResult]:
    """
    Generate multiple query variants and aggregate results
    
    Why this helps:
    - Single query might miss relevant chunks due to wording
    - Multiple perspectives improve recall
    - Reciprocal rank fusion combines results
    """
    # Expand query
    queries = expand_query(query)[:num_queries]
    
    # Collect results from all queries
    all_results = {}  # chunk_id -> list of (rank, result)
    
    for q in queries:
        # results = embeddings_db.query(q, top_k=top_k * 2)
        # For each result, track its rank
        pass  # Placeholder - implement with actual DB
    
    # Reciprocal Rank Fusion
    # Score = sum(1 / (k + rank)) for each query where chunk appears
    k = 60  # Constant from RRF paper
    
    fused_scores = {}
    for chunk_id, rankings in all_results.items():
        score = sum(1 / (k + rank) for rank, _ in rankings)
        fused_scores[chunk_id] = score
    
    # Sort and return top results
    # ...
    
    return []  # Placeholder


# =============================================================================
# 7. COMPLETE RETRIEVAL PIPELINE
# =============================================================================

def retrieve(
    query: str,
    chunks: List[Dict],
    embeddings_db,  # Your vector DB
    strategy: str = "hybrid_rerank",
    top_k: int = 5,
) -> List[Dict]:
    """
    Complete retrieval pipeline
    
    Strategies:
    - "simple": Just semantic search
    - "hybrid": Semantic + keyword
    - "hybrid_rerank": Semantic + keyword + cross-encoder reranking
    - "full": All techniques (expand query, hybrid, section boost, rerank)
    """
    
    if strategy == "simple":
        # Just vector search
        # results = embeddings_db.query(query, top_k=top_k)
        pass
    
    elif strategy == "hybrid":
        results = hybrid_search(query, chunks, embeddings_db, top_k=top_k * 2)
        results = results[:top_k]
    
    elif strategy == "hybrid_rerank":
        # Get more candidates with hybrid search
        results = hybrid_search(query, chunks, embeddings_db, top_k=top_k * 3)
        # Boost relevant sections
        results = section_boosted_retrieval(results, query)
        # Re-rank top candidates
        results = rerank_with_cross_encoder(query, results, top_k=top_k)
    
    elif strategy == "full":
        # Expand query first
        queries = expand_query(query)
        
        # Aggregate results from all query variants
        all_results = []
        for q in queries[:3]:
            results = hybrid_search(q, chunks, embeddings_db, top_k=top_k * 2)
            all_results.extend(results)
        
        # Deduplicate by chunk_id, keeping highest score
        seen = {}
        for r in all_results:
            if r.chunk_id not in seen or r.final_score > seen[r.chunk_id].final_score:
                seen[r.chunk_id] = r
        
        results = list(seen.values())
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        # Section boosting
        results = section_boosted_retrieval(results, query)
        
        # Re-rank
        results = rerank_with_cross_encoder(query, results, top_k=top_k)
    
    # Convert to context format
    contexts = [
        {
            'text': r.text,
            'metadata': r.metadata,
            'score': r.final_score,
        }
        for r in results[:top_k]
    ]
    
    return contexts


# =============================================================================
# 8. EVALUATION UTILITIES
# =============================================================================

def evaluate_retrieval(
    queries: List[str],
    ground_truth: Dict[str, List[str]],  # query -> list of relevant chunk_ids
    retrieval_fn,
    k_values: List[int] = [1, 3, 5, 10],
) -> Dict[str, float]:
    """
    Evaluate retrieval performance
    
    Metrics:
    - Precision@K: What fraction of retrieved docs are relevant?
    - Recall@K: What fraction of relevant docs are retrieved?
    - MRR: Where does the first relevant doc appear?
    """
    precisions = {k: [] for k in k_values}
    recalls = {k: [] for k in k_values}
    mrr_scores = []
    
    for query in queries:
        relevant = set(ground_truth.get(query, []))
        if not relevant:
            continue
        
        retrieved = retrieval_fn(query)
        retrieved_ids = [r['metadata']['chunk_id'] for r in retrieved]
        
        # MRR
        for i, rid in enumerate(retrieved_ids):
            if rid in relevant:
                mrr_scores.append(1 / (i + 1))
                break
        else:
            mrr_scores.append(0)
        
        # Precision and Recall at K
        for k in k_values:
            top_k = set(retrieved_ids[:k])
            hits = len(top_k & relevant)
            
            precisions[k].append(hits / k)
            recalls[k].append(hits / len(relevant))
    
    # Average metrics
    results = {
        'MRR': sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0,
    }
    
    for k in k_values:
        results[f'P@{k}'] = sum(precisions[k]) / len(precisions[k]) if precisions[k] else 0
        results[f'R@{k}'] = sum(recalls[k]) / len(recalls[k]) if recalls[k] else 0
    
    return results


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

def main():
    print("Advanced Retrieval Strategies for RAG")
    print("=" * 60)
    
    # Test query expansion
    print("\n1. QUERY EXPANSION")
    test_queries = [
        "What ML methods did they use?",
        "What are the limitations?",
        "How does the CNN architecture work?",
    ]
    
    for q in test_queries:
        expanded = expand_query(q)
        print(f"\nOriginal: {q}")
        print(f"Expanded: {expanded}")
    
    # Test section detection
    print("\n\n2. SECTION DETECTION")
    for q in test_queries:
        sections = detect_question_type(q)
        print(f"\n'{q}'")
        print(f"  Likely sections: {sections}")
    
    # Test BM25 scoring
    print("\n\n3. KEYWORD SCORING (BM25-like)")
    doc = "This paper presents a novel machine learning method for image classification using convolutional neural networks."
    queries = [
        "machine learning method",
        "image classification CNN",
        "natural language processing",
    ]
    
    for q in queries:
        score = compute_bm25_score(q, doc)
        print(f"Query: '{q}' -> Score: {score:.3f}")
    
    print("\n\n4. RECOMMENDED PIPELINE")
    print("""
    For best results, use this pipeline:
    
    1. INDEXING TIME:
       - Use hierarchical chunking (section + paragraph levels)
       - Add synthetic chunks for common question types
       - Store rich metadata (section, page, parent_id)
    
    2. QUERY TIME:
       a. Expand query (synonyms, acronyms)
       b. Hybrid search (semantic + BM25)
       c. Section boosting (based on question type)
       d. Re-rank top 15-20 with cross-encoder
       e. Return top 5 for generation
    
    3. GENERATION TIME:
       - Expand to parent chunks for context
       - Include section names in prompt
       - Require citations
    """)


if __name__ == "__main__":
    main()