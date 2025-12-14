"""
Test script to verify the entire RAG pipeline works end-to-end
"""
from pathlib import Path
from parse_pdf import extract_text_from_pdf, remove_repeated_headers_footers
from chunk_text import simple_tokenize, chunk_tokens
from embeddings import embed_chunks, store_in_pinecone
import os

def test_pipeline():
    print("=" * 60)
    print("TESTING RAG PIPELINE")
    print("=" * 60)

    # Step 1: Test PDF extraction
    print("\n[STEP 1] Testing PDF extraction...")
    pdf_path = Path("test_papers/research_paper.pdf")

    if not pdf_path.exists():
        print(f"❌ ERROR: {pdf_path} not found")
        return False

    try:
        pages_text = extract_text_from_pdf(pdf_path)
        print(f"✓ Extracted {len(pages_text)} pages")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

    # Step 2: Test header removal
    print("\n[STEP 2] Testing header removal...")
    try:
        pages_text_cleaned = remove_repeated_headers_footers(pages_text)
        print(f"✓ Cleaned {len(pages_text_cleaned)} pages")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

    # Step 3: Test chunking
    print("\n[STEP 3] Testing chunking...")
    try:
        full_text = "\n\n".join(pages_text_cleaned)
        tokens = simple_tokenize(full_text)
        print(f"✓ Tokenized: {len(tokens)} tokens")

        chunks = chunk_tokens(tokens, chunk_size=500, overlap=50)
        print(f"✓ Created {len(chunks)} chunks")
        print(f"  First chunk preview: {chunks[0][:100]}...")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

    # Step 4: Test embedding generation (requires API keys)
    print("\n[STEP 4] Testing embedding generation...")

    # Check for API keys
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not set - skipping embedding test")
        return True

    if not os.environ.get("PINECONE_API_KEY"):
        print("⚠️  WARNING: PINECONE_API_KEY not set - skipping embedding test")
        return True

    try:
        # Create metadata for chunks
        metadata_list = []
        for i in range(len(chunks)):
            metadata_list.append({
                "pdf_id": "research_paper",
                "chunk_index": i,
                "text": chunks[i][:1000]  # Store first 1000 chars for display
            })

        # Test with just first 3 chunks to save API costs
        print("  Testing with first 3 chunks only (to save API costs)...")
        test_chunks = chunks[:3]
        test_metadata = metadata_list[:3]

        vectors = embed_chunks(test_chunks, test_metadata)
        print(f"✓ Generated {len(vectors)} embeddings")
        print(f"  Vector dimension: {len(vectors[0]['values'])}")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 5: Test Pinecone storage
    print("\n[STEP 5] Testing Pinecone storage...")

    if not os.environ.get("PINECONE_INDEX_NAME"):
        print("⚠️  WARNING: PINECONE_INDEX_NAME not set - skipping storage test")
        return True

    try:
        store_in_pinecone(vectors)
        print(f"✓ Stored {len(vectors)} vectors in Pinecone")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_pipeline()
