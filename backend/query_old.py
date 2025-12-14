# takes a relevant question, converts it to an embedding, searches Pinecone for the 5 most similar chunks, and returns chunks with similarity scores
from openai import OpenAI
import os
from pinecone import Pinecone
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# given a question, embed it and search the vector DB for top_k most similar chunks
def query_vector_db(question: str, top_k: int = 5):
    # embed the question
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    )
    question_embedding = response.data[0].embedding

    # query pinecone
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)

    results = index.query(
        vector=question_embedding,
        top_k=top_k,
        include_metadata=True
    )

    # format and return results
    matched_chunks = []
    for match in results['matches']:
        matched_chunks.append({
            'id': match['id'],
            'score': match['score'],
            'text': match['metadata'].get('text', 'No text available'),
            'pdf_id': match['metadata'].get('pdf_id', 'Unknown'),
            'chunk_index': match['metadata'].get('chunk_index', -1)
        })

    return matched_chunks


def print_results(question: str, results: list):
    print("\n" + "=" * 80)
    print(f"QUERY: {question}")
    print("=" * 80)

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, 1):
        print(f"\n[RESULT {i}] (Score: {result['score']:.4f})")
        print(f"Source: {result['pdf_id']} - Chunk {result['chunk_index']}")
        print("-" * 80)
        # Print first 500 characters of the chunk
        text_preview = result['text'][:500] + "..." if len(result['text']) > 500 else result['text']
        print(text_preview)
        print()


def main():

    test_questions = [
        "How do students use mobile devices for learning English?",
        "What are the benefits of mobile learning?",
        "What methodology was used in this study?",
        "What are the limitations of this research?",
        "How many participants were in the study?"
    ]

    print("\n" + "#" * 80)
    print("TESTING RETRIEVAL WITH SAMPLE QUESTIONS")
    print("#" * 80)

    for question in test_questions:
        results = query_vector_db(question, top_k=5)
        print_results(question, results)
        print("\n")


if __name__ == "__main__":
    main()
