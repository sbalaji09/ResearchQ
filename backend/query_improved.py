"""
Improved query script with section-aware retrieval and better ranking
"""
from openai import OpenAI
import os
from pinecone import Pinecone
from dotenv import load_dotenv
from pathlib import Path
from retrieval import (
    detect_question_type,
    compute_bm25_score,
    expand_query,
)

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))


def query_with_section_boost(
    question: str,
    top_k: int = 10,
    boost_factor: float = 1.5,
) -> list:
    """
    Query with section-aware boosting for better precision

    Improvements:
    1. Detects question type (methods, results, limitations, etc.)
    2. Boosts chunks from relevant sections
    3. Hybrid ranking: semantic + keyword + section relevance
    """

    # Step 1: Embed the question
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    )
    question_embedding = response.data[0].embedding

    # Step 2: Get candidates from Pinecone (get more than needed)
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)

    results = index.query(
        vector=question_embedding,
        top_k=top_k * 2,  # Get extra candidates for reranking
        include_metadata=True
    )

    # Step 3: Detect relevant sections based on question
    relevant_sections = detect_question_type(question)

    # Step 4: Hybrid scoring (semantic + keyword + section boost)
    scored_results = []

    for match in results['matches']:
        semantic_score = match['score']
        text = match['metadata'].get('text', '')
        section = match['metadata'].get('section', '')

        # Keyword score (BM25-like)
        keyword_score = compute_bm25_score(question, text)

        # Section boost
        section_boost = boost_factor if section in relevant_sections else 1.0

        # Combined score
        final_score = (semantic_score * 0.7 + keyword_score * 0.3) * section_boost

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

    # Step 5: Re-rank by final score
    scored_results.sort(key=lambda x: x['final_score'], reverse=True)

    # Step 6: Return top K
    return scored_results[:top_k]


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
            print(f"     Semantic: {result['semantic_score']:.4f}")
            print(f"     Keyword: {result['keyword_score']:.4f}")
            print(f"     Section Boost: {result.get('section_boost', 1.0):.2f}x")

        print("-" * 80)

        # Show text preview
        text = result.get('text', '')
        preview = text[:400] + "..." if len(text) > 400 else text
        print(preview)


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
        results = query_with_section_boost(question, top_k=5, boost_factor=1.5)
        print_results(question, results, show_scores=True)
        print("\n")


if __name__ == "__main__":
    main()
