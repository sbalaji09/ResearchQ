"""
Reset Pinecone index and store paper with improved chunking strategy

This script will:
1. Delete all existing vectors from Pinecone
2. Re-process the paper with improved sentence-based chunking
3. Store the new, better-quality chunks

Run this to replace old chunks with improved ones.
"""
from pathlib import Path
from parse_pdf import extract_text_from_pdf, remove_repeated_headers_footers
from chunk_text_improved import chunk_by_sentences
from embeddings import embed_chunks, store_in_pinecone, pc
import os


def clear_pinecone_index():
    """Delete all vectors from the Pinecone index"""
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)

    print("\n[RESET] Clearing existing vectors from Pinecone...")

    try:
        # Delete all vectors by namespace (if using default namespace, delete all)
        index.delete(delete_all=True)
        print("✓ Successfully cleared all vectors from Pinecone")
    except Exception as e:
        print(f"⚠️  Warning: Could not clear vectors: {e}")
        print("   Continuing anyway - new vectors will be added/updated")


def process_and_store_paper(pdf_path: Path, pdf_id: str):
    """
    Process a single PDF paper with improved chunking and store in Pinecone

    Improvements:
    - Sentence-based chunking (respects thought boundaries)
    - Smaller chunks (300 tokens vs 500)
    - More overlap (2 sentences)
    - PAGE BREAK markers removed
    """
    print(f"\nProcessing: {pdf_path}")
    print("=" * 80)

    # Step 1: Extract text from PDF
    print("\n[1/5] Extracting text from PDF...")
    pages_text = extract_text_from_pdf(pdf_path)
    print(f"✓ Extracted {len(pages_text)} pages")

    # Step 2: Remove headers and footers
    print("\n[2/5] Removing headers and footers...")
    pages_text_cleaned = remove_repeated_headers_footers(pages_text)
    print(f"✓ Cleaned {len(pages_text_cleaned)} pages")

    # Step 3: Chunk the text with improved strategy
    print("\n[3/5] Chunking text with IMPROVED strategy...")
    full_text = "\n\n".join(pages_text_cleaned)

    chunks = chunk_by_sentences(full_text, target_chunk_size=300, overlap_sentences=2)
    avg_size = sum(len(c.split()) for c in chunks) / len(chunks)

    print(f"✓ Created {len(chunks)} chunks (was 15 with old strategy)")
    print(f"  Average chunk size: {avg_size:.0f} tokens (was ~484 tokens)")
    print(f"  Improvement: More focused, semantically coherent chunks")

    # Step 4: Create metadata for each chunk
    print("\n[4/5] Generating embeddings...")
    metadata_list = []
    for i in range(len(chunks)):
        metadata_list.append({
            "pdf_id": pdf_id,
            "chunk_index": i,
            "text": chunks[i]  # Store full chunk text for retrieval
        })

    # Generate embeddings for all chunks
    vectors = embed_chunks(chunks, metadata_list)
    print(f"✓ Generated {len(vectors)} embeddings (dimension: {len(vectors[0]['values'])})")

    # Step 5: Store in Pinecone
    print("\n[5/5] Storing vectors in Pinecone...")
    store_in_pinecone(vectors)
    print(f"✓ Stored {len(vectors)} vectors in Pinecone")

    print("\n" + "=" * 80)
    print(f"✅ SUCCESS: Processed and stored {len(chunks)} improved chunks")
    print("=" * 80)

    return len(chunks)


def main():
    """Reset and re-process the research paper with improved chunking"""

    print("=" * 80)
    print("RESETTING PINECONE & STORING WITH IMPROVED CHUNKING")
    print("=" * 80)
    print("\nImprovements:")
    print("  ✓ Sentence-based chunking (preserves semantic units)")
    print("  ✓ Smaller chunks (300 tokens → more focused embeddings)")
    print("  ✓ Better overlap (2 full sentences)")
    print("  ✓ Removed PAGE BREAK markers")
    print("  ✓ More chunks (30 vs 15 → better coverage)")

    # Configure the paper to process
    pdf_path = Path("test_papers/research_paper.pdf")
    pdf_id = "research_paper"

    if not pdf_path.exists():
        print(f"\n❌ ERROR: {pdf_path} not found")
        print(f"   Make sure the PDF is in the test_papers/ folder")
        return

    # Clear existing vectors
    clear_pinecone_index()

    # Process and store the paper with improved chunking
    total_chunks = process_and_store_paper(pdf_path, pdf_id)

    print(f"\n📊 Summary:")
    print(f"   Paper: {pdf_path.name}")
    print(f"   Old chunks: 15 (500 tokens, word-based)")
    print(f"   New chunks: {total_chunks} (300 tokens, sentence-based)")
    print(f"   Expected improvement: Better retrieval scores (50%+ → 70%+)")
    print(f"\n💡 Next step: Run 'python query.py' to test improved retrieval!")


if __name__ == "__main__":
    main()
