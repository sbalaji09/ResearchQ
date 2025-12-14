"""
Script to process a full research paper and store all chunks in Pinecone

This script:
1. Extracts text from a PDF
2. Removes headers/footers
3. Chunks the text into 500-token pieces with 50-token overlap
4. Generates embeddings for each chunk
5. Stores all embeddings in Pinecone with metadata
"""
from pathlib import Path
from parse_pdf import extract_text_from_pdf, remove_repeated_headers_footers
from chunk_text import simple_tokenize, chunk_tokens
from embeddings import embed_chunks, store_in_pinecone


def process_and_store_paper(pdf_path: Path, pdf_id: str):
    """
    Process a single PDF paper and store all its chunks in Pinecone

    Args:
        pdf_path: Path to the PDF file
        pdf_id: Unique identifier for this paper (e.g., "research_paper")
    """
    print(f"Processing: {pdf_path}")
    print("=" * 80)

    # Step 1: Extract text from PDF
    print("\n[1/5] Extracting text from PDF...")
    pages_text = extract_text_from_pdf(pdf_path)
    print(f"✓ Extracted {len(pages_text)} pages")

    # Step 2: Remove headers and footers
    print("\n[2/5] Removing headers and footers...")
    pages_text_cleaned = remove_repeated_headers_footers(pages_text)
    print(f"✓ Cleaned {len(pages_text_cleaned)} pages")

    # Step 3: Chunk the text
    print("\n[3/5] Chunking text...")
    full_text = "\n\n".join(pages_text_cleaned)
    tokens = simple_tokenize(full_text)
    print(f"✓ Tokenized: {len(tokens)} tokens")

    chunks = chunk_tokens(tokens, chunk_size=500, overlap=50)
    print(f"✓ Created {len(chunks)} chunks")

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
    print(f"✅ SUCCESS: Processed and stored {len(chunks)} chunks from {pdf_path.name}")
    print("=" * 80)

    return len(chunks)


def main():
    """Process the research paper and store all chunks"""

    # Configure the paper to process
    pdf_path = Path("test_papers/research_paper.pdf")
    pdf_id = "research_paper"

    if not pdf_path.exists():
        print(f"❌ ERROR: {pdf_path} not found")
        print(f"   Make sure the PDF is in the test_papers/ folder")
        return

    # Process and store the paper
    total_chunks = process_and_store_paper(pdf_path, pdf_id)

    print(f"\n📊 Summary:")
    print(f"   Paper: {pdf_path.name}")
    print(f"   Total chunks stored: {total_chunks}")
    print(f"   Ready for querying!")
    print(f"\n💡 Next step: Run 'python query.py' to test retrieval")


if __name__ == "__main__":
    main()
