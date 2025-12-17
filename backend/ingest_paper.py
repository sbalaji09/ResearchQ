"""
Main script to ingest research papers into the vector database
Uses improved hierarchical chunking and rich metadata
"""
from pathlib import Path
from parse_pdf_enhanced import extract_text_from_pdf_enhanced
from chunk_text_improved import chunk_document, chunks_to_documents
from embeddings import embed_chunks, store_in_pinecone
import os


def ingest_paper(pdf_path: Path, pdf_id: str, clear_existing: bool = False):
    """
    Complete pipeline to ingest a research paper

    Args:
        pdf_path: Path to PDF file
        pdf_id: Unique identifier for this paper
        clear_existing: Whether to clear existing vectors first
    """
    print("=" * 80)
    print(f"INGESTING PAPER: {pdf_path.name}")
    print("=" * 80)

    # Optional: Clear existing vectors
    if clear_existing:
        print("\n[0/5] Clearing existing vectors from Pinecone...")
        try:
            from embeddings import pc
            index_name = os.environ.get("PINECONE_INDEX_NAME")
            index = pc.Index(index_name)
            index.delete(delete_all=True)
            print("✓ Cleared all existing vectors")
        except Exception as e:
            print(f"⚠️  Warning: Could not clear vectors: {e}")

    # Step 1: Extract text from PDF
    print("\n[1/5] Extracting text from PDF...")
    pages_text = extract_text_from_pdf_enhanced(pdf_path)
    print(f"✓ Extracted {len(pages_text)} pages")

    # # Step 2: Remove headers and footers
    # print("\n[2/5] Removing headers and footers...")
    # pages_text_cleaned = remove_repeated_headers_footers(pages_text)
    # print(f"✓ Cleaned {len(pages_text_cleaned)} pages")

    # Step 3: Hierarchical chunking with section awareness
    print("\n[3/5] Creating hierarchical chunks...")
    full_text = "\n\n".join(pages_text)

    # Use hierarchical strategy for best retrieval
    chunk_objects = chunk_document(
        text=full_text,
        document_id=pdf_id,
        strategy="hierarchical",  # Section-aware, multi-level chunks
        chunk_size=400,            # Optimal: enough context, still focused
        overlap=3,                 # More overlap for continuity
        add_synthetic=True,        # Add synthetic summary chunks
    )

    print(f"✓ Created {len(chunk_objects)} chunks")

    # Count by type
    type_counts = {}
    section_counts = {}
    for chunk in chunk_objects:
        ct = chunk.metadata.get('chunk_type', 'unknown')
        type_counts[ct] = type_counts.get(ct, 0) + 1

        sec = chunk.metadata.get('section', 'unknown')
        section_counts[sec] = section_counts.get(sec, 0) + 1

    print(f"  By type: {dict(type_counts)}")
    print(f"  By section: {dict(section_counts)}")

    # Step 4: Convert to embeddings format
    print("\n[4/5] Generating embeddings...")

    # Convert chunks to format needed by embeddings.py
    chunks_text = [chunk.text for chunk in chunk_objects]
    chunks_metadata = []

    for i, chunk in enumerate(chunk_objects):
        # Keep the rich metadata from hierarchical chunking
        metadata = {
            'pdf_id': pdf_id,
            'text': chunk.text,  # Store full text for retrieval
            'chunk_index': i,    # Add sequential index for unique ID
            **chunk.metadata     # Include section, chunk_type, etc.
        }
        chunks_metadata.append(metadata)

    # Generate embeddings for all chunks
    vectors = embed_chunks(chunks_text, chunks_metadata)
    print(f"✓ Generated {len(vectors)} embeddings")
    print(f"  Dimension: {len(vectors[0]['values'])}")

    # Step 5: Store in Pinecone
    print("\n[5/5] Storing vectors in Pinecone...")
    store_in_pinecone(vectors)
    print(f"✓ Stored {len(vectors)} vectors")

    print("\n" + "=" * 80)
    print("✅ SUCCESS!")
    print("=" * 80)
    print(f"  Paper: {pdf_path.name}")
    print(f"  Total chunks: {len(chunk_objects)}")
    print(f"  Chunk types: {', '.join(type_counts.keys())}")
    print(f"\n💡 Next: Run 'python query_improved.py' to test retrieval")

    return len(chunk_objects)


def main():
    """Ingest the research paper"""

    # Configure paper
    pdf_path = Path("test_papers/research_paper.pdf")
    pdf_id = "research_paper"

    if not pdf_path.exists():
        print(f"❌ ERROR: {pdf_path} not found")
        print(f"   Place your PDF in: test_papers/research_paper.pdf")
        return

    # Ingest with fresh start
    total_chunks = ingest_paper(
        pdf_path=pdf_path,
        pdf_id=pdf_id,
        clear_existing=True  # Clear old chunks first
    )

    print(f"\n📊 Comparison:")
    print(f"   Old approach: 15 chunks (500 tokens, word-based)")
    print(f"   New approach: {total_chunks} chunks (hierarchical, section-aware)")
    print(f"   Expected improvement: 50% → 75%+ retrieval scores")


if __name__ == "__main__":
    main()
