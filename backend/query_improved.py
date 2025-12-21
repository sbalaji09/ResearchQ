import re
from openai import OpenAI
import os
from pinecone import Pinecone
from dotenv import load_dotenv
from pathlib import Path
from generation import answer_generation
from retrieval import (
    detect_question_type,
    compute_bm25_score,
    expand_query,
)

from exceptions import NoRelevantChunksError, LowRelevanceError, RetrievalError, GenerationError
from cache import embedding_cache, detect_query_complexity, get_model_for_complexity

_cross_encoder = None

def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    return _cross_encoder

MIN_RELEVANCE_SCORE = 0.25  # Below this, results are likely irrelevant
LOW_RELEVANCE_WARNING = 0.4  # Below this, warn user about low confidence

SEMANTIC_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4
SECTION_BOOST = 2.0
RERANK_WEIGHT = 0.7
HYBRID_WEIGHT = 0.3
RERANK_CANDIDATES = 20

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# query with section-aware boosting and optional reranking for better precision
def query_with_section_boost(
    question: str,
    top_k: int = 10,
    boost_factor: float = 2.0,  # Stronger boost for better signal
    use_reranking: bool = True,
    pdf_ids: list[str] = None,
) -> list:
    # Step 1: Expand query for better recall
    expanded_queries = expand_query(question)
    all_candidates = {}  # chunk_id -> best result

    for query_variant in expanded_queries[:3]:  # Use top 3 variants
        # Embed the query
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query_variant
        )
        query_embedding = get_embedding_cached(query_variant)

        # Get candidates from Pinecone
        index_name = os.environ.get("PINECONE_INDEX_NAME")
        index = pc.Index(index_name)

        query_filter = None
        if pdf_ids:
            if len(pdf_ids) == 1:
                query_filter = {"pdf_id": {"$eq": pdf_ids[0]}}
            else:
                query_filter = {"pdf_id": {"$in": pdf_ids}}

        results = index.query(
            vector=query_embedding,
            top_k=top_k * 3,  # Get more candidates for reranking
            include_metadata=True,
            filter=query_filter
        )

        # Aggregate results (keep highest scoring variant)
        for match in results['matches']:
            chunk_id = match['id']
            if chunk_id not in all_candidates or match['score'] > all_candidates[chunk_id]['score']:
                all_candidates[chunk_id] = match

    # Step 2: Detect relevant sections based on question
    relevant_sections = detect_question_type(question)

    # Step 3: Hybrid scoring (semantic + keyword + section boost)
    scored_results = []

    for chunk_id, match in all_candidates.items():
        semantic_score = match['score']
        text = match['metadata'].get('text', '')
        section = match['metadata'].get('section', '')

        # Keyword score (BM25-like)
        keyword_score = compute_bm25_score(question, text)

        # Section boost (stronger signal)
        section_boost = boost_factor if section in relevant_sections else 1.0

        # Combined score with adjusted weights
        # Give more weight to keyword matching for precision
        final_score = (semantic_score * 0.6 + keyword_score * 0.4) * section_boost

        scored_results.append({
            'id': match['id'],
            'semantic_score': semantic_score,
            'keyword_score': keyword_score,
            'section_boost': section_boost,
            'final_score': final_score,
            'text': text,
            'section': section,
            'chunk_type': match['metadata'].get('chunk_type', 'unknown'),
            'metadata': match['metadata'],
        })

    # Step 4: Re-rank by final score
    scored_results.sort(key=lambda x: x['final_score'], reverse=True)

    # Step 5: Optional cross-encoder reranking
    if use_reranking and len(scored_results) > 0:
        try:
            from sentence_transformers import CrossEncoder

            # Use a lightweight cross-encoder
            model = get_cross_encoder()

            # Take top candidates for reranking (expensive operation)
            candidates_to_rerank = scored_results[:min(20, len(scored_results))]

            # Prepare pairs
            pairs = [(question, r['text']) for r in candidates_to_rerank]

            # Get reranking scores
            rerank_scores = model.predict(pairs)

            # Update scores
            # Normalize rerank scores to [0, 1] range using sigmoid-like transformation
            min_rerank = min(rerank_scores)
            max_rerank = max(rerank_scores)
            range_rerank = max_rerank - min_rerank if max_rerank != min_rerank else 1.0

            for i, result in enumerate(candidates_to_rerank):
                # Normalize rerank score to [0, 1]
                raw_rerank = float(rerank_scores[i])
                normalized_rerank = (raw_rerank - min_rerank) / range_rerank

                result['rerank_score'] = normalized_rerank
                # Combine: prioritize reranker but keep hybrid signal
                result['final_score'] = 0.7 * normalized_rerank + 0.3 * result['final_score']

            # Re-sort by new scores
            scored_results.sort(key=lambda x: x.get('final_score', 0), reverse=True)

        except ImportError:
            print("⚠️  sentence-transformers not installed, skipping reranking")
            print("   Install with: pip install sentence-transformers")

    # Step 6: Return top K
    return scored_results[:top_k]

# retrieval -> generation
def content_generator(question: str, top_k: int = 5, pdf_ids: list[str]=None, conversation_history: list = None) -> str:
    # Step 1: Retrieve relevant chunks with metadata
    try:
        results = query_with_section_boost(
            question=question,
            top_k=top_k,
            boost_factor=2.0,
            use_reranking=True,
            pdf_ids=pdf_ids
        )
    except Exception as e:
        # Fallback message if retrieval itself fails
        return {
            "answer": "I encountered an error while searching the documents. Please try again.",
            "citations": [],
            "error": f"Retrieval error: {str(e)}",
            "error_code": "RETRIEVAL_ERROR"
        }
    
    if not results:
        return {
            "answer": "No documents have been uploaded yet. Please upload a PDF first.",
            "citations": [],
            "error_code": "NO_DOCUMENTS"
        }

    best_score = max(r.get('final_score', 0) for r in results)
    
    if best_score < MIN_RELEVANCE_SCORE:
        return {
            "answer": "I couldn't find information directly relevant to your question in the uploaded documents. Try rephrasing your question or uploading more relevant papers.",
            "citations": [],
            "error_code": "LOW_RELEVANCE",
            "best_score": best_score
        }
    
    chunks: list[str] = []
    metadata = {
        "sections": [],
        "chunk_ids": [],
        "scores": [],
        "documents": [],
    }

    for i, result in enumerate(results):
        # Robust access with defaults
        text = result.get("text") or result.get("metadata", {}).get("text", "")
        if not text:
            continue

        chunks.append(text)
        metadata["sections"].append(result.get("section", "Unknown"))
        metadata["chunk_ids"].append(result.get("id", f"chunk_{i}"))
        metadata["scores"].append(result.get("final_score", 0.0))

        doc_id = result.get("metadata", {}).get("pdf_id", "unknown")
        metadata["documents"].append(doc_id)

    if not chunks:
        return {
            "answer": "I found some matches but couldn't extract the text. The documents may be corrupted.",
            "citations": [],
            "error_code": "EMPTY_CHUNKS"
        }
    
    # Step 3: Generate answer with metadata for citations
    try:
        result = answer_generation(chunks, question, metadata,conversation_history=conversation_history)
        if result is None:
            return {
                "answer": "I encountered an error generating the answer. Please try again.",
                "citations": [],
                "error_code": "GENERATION_FAILED"
            }
        if best_score < LOW_RELEVANCE_WARNING:
            result["warning"] = "The retrieved information may not be directly relevant to your question."
            result["confidence"] = "low"
        else:
            result["confidence"] = "high" if best_score > 0.6 else "medium"
        
        return result
    except Exception as e:
        return {
            "answer": "I encountered an error while generating the answer. Please try again.",
            "citations": [],
            "error": str(e),
            "error_code": "GENERATION_ERROR"
        }

def print_results(question: str, results: list, show_scores: bool = True):
    """Pretty print results with scoring breakdown"""
    print("\n" + "=" * 80)
    print(f"QUERY: {question}")
    print("=" * 80)

    if not results:
        print("No results found.")
        return

    # Show detected sections
    relevant_sections = detect_question_type(question)
    if relevant_sections:
        print(f"\n🎯 Detected relevant sections: {', '.join(relevant_sections)}")

    for i, result in enumerate(results, 1):
        section_marker = "🔥" if result.get('section_boost', 1.0) > 1.0 else "  "

        print(f"\n{section_marker} [RESULT {i}]")
        print(f"   Section: {result.get('section', 'Unknown')}")
        print(f"   Type: {result.get('chunk_type', 'unknown')}")

        if show_scores:
            print(f"   Scores:")
            print(f"     Final: {result['final_score']:.4f}")
            if 'rerank_score' in result:
                print(f"     Rerank: {result['rerank_score']:.4f}")
            print(f"     Semantic: {result['semantic_score']:.4f}")
            print(f"     Keyword: {result['keyword_score']:.4f}")
            print(f"     Section Boost: {result.get('section_boost', 1.0):.2f}x")

        print("-" * 80)

        # Show text preview
        text = result.get('text', '')
        preview = text[:400] + "..." if len(text) > 400 else text
        print(preview)

# get embedding with caching
def get_embedding_cached(text: str) -> list:
    def compute():
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input = text.strip()
        )
        return response.data[0].embedding
    
    return embedding_cache.get_or_compute(text, compute)


def main():
    """Test retrieval with improved pipeline"""

    print("=" * 80)
    print("TESTING IMPROVED RETRIEVAL")
    print("=" * 80)
    print("\nImprovements:")
    print("  ✓ Section-aware boosting (methods → Methods section)")
    print("  ✓ Hybrid scoring (semantic + keyword)")
    print("  ✓ Hierarchical chunks (section + paragraph levels)")
    print("  ✓ BM25 keyword matching")

    # Test questions
    test_questions = [
        "How do students use mobile devices for learning English?",
        "What are the benefits of mobile learning?",
        "What methodology was used in this study?",
        "What are the limitations of this research?",
        "How many participants were in the study?",
    ]

    for question in test_questions:
        results = query_with_section_boost(question, top_k=5, boost_factor=2.0, use_reranking=True)
        print_results(question, results, show_scores=True)
        print("\n")
        
# boost for exact phrase match
def compute_exact_match_boost(query: str, text: str) -> float:
    query_lower = query.lower()
    text_lower = text.lower()
    
    quoted = re.findall(r'"([^"]+)"', query)
    for phrase in quoted:
        if phrase.lower() in text_lower:
            return 1.5  # 50% boost for exact match
    
    query_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', query))
    text_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', text))
    
    if query_numbers and query_numbers & text_numbers:
        return 1.2
    
    return 1.0
if __name__ == "__main__":
    main()
