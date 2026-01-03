# calls openai's to convert text chunks into embeddings where each vector is stored in Pinecone with metadata
from openai import OpenAI
import os
from pinecone import Pinecone, ServerlessSpec
from concurrent.futures import ThreadPoolExecutor, as_completed

# Lazy initialization of clients
_openai_client = None
_pinecone_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _openai_client

def get_pinecone_client():
    global _pinecone_client
    if _pinecone_client is None:
        _pinecone_client = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    return _pinecone_client

# gets the embedding for one piece of text
def get_embedding(text: str):
    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    response = get_openai_client().embeddings.create(
        model="text-embedding-3-small",
        input=cleaned_text
    )

    return response.data[0].embedding

# embeds chunks of data using OpenAI embedding model
def embed_chunks(chunks: list[str], metadata: list[dict], batch_size: int = 64):
    if len(chunks) != len(metadata):
        return

    vectors = []

    for start in range(0, len(chunks), batch_size):
        end = min(start+batch_size, len(chunks))
        batch_chunks = chunks[start: end]
        batch_metadata = metadata[start:end]

        response = get_openai_client().embeddings.create(
            model="text-embedding-3-small",
            input=batch_chunks
        )
        batch_embeddings = [item.embedding for item in response.data]

        for i, (embedding, meta) in enumerate(zip(batch_embeddings, batch_metadata)):
            vector_id = f"{meta['pdf_id']}_chunk_{meta['chunk_index']}"

            vectors.append({"id": vector_id, "values": embedding, "metadata": meta})

    return vectors


def _embed_batch(batch_chunks: list[str], batch_metadata: list[dict], client: OpenAI) -> list[dict]:
    """Helper function to embed a single batch - used for parallel processing."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=batch_chunks
    )
    batch_embeddings = [item.embedding for item in response.data]

    vectors = []
    for embedding, meta in zip(batch_embeddings, batch_metadata):
        vector_id = f"{meta['pdf_id']}_chunk_{meta['chunk_index']}"
        vectors.append({"id": vector_id, "values": embedding, "metadata": meta})

    return vectors


def embed_chunks_parallel(chunks: list[str], metadata: list[dict], batch_size: int = 2048, max_workers: int = 6):
    """
    Parallel embedding generation - processes multiple batches concurrently.

    Optimizations:
    - batch_size=2048: OpenAI allows up to 2048 inputs per request
    - Most papers (30-100 chunks) now fit in a single API call
    - Reduced API overhead = faster uploads
    """
    if len(chunks) != len(metadata):
        return []

    if not chunks:
        return []

    # Prepare batches - OpenAI text-embedding-3-small supports up to 2048 inputs
    batches = []
    for start in range(0, len(chunks), batch_size):
        end = min(start + batch_size, len(chunks))
        batches.append((chunks[start:end], metadata[start:end]))

    # If only one batch, no need for parallelization (most common case now)
    if len(batches) == 1:
        return _embed_batch(batches[0][0], batches[0][1], get_openai_client())

    # Process batches in parallel
    all_vectors = []
    client = get_openai_client()

    with ThreadPoolExecutor(max_workers=min(max_workers, len(batches))) as executor:
        futures = {
            executor.submit(_embed_batch, batch_chunks, batch_meta, client): idx
            for idx, (batch_chunks, batch_meta) in enumerate(batches)
        }

        # Collect results in order
        results = [None] * len(batches)
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    # Flatten results
    for batch_vectors in results:
        all_vectors.extend(batch_vectors)

    return all_vectors

# stores vectors in pinecone based on a batch limit
def store_in_pinecone(vectors, batch_limit=100):
    """
    Store vectors in Pinecone with parallel batch upserts.

    Optimizations:
    - Parallel upserts for multiple batches
    - batch_limit=100 is Pinecone's recommended max per upsert
    """
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = get_pinecone_client().Index(index_name)

    # Convert to upsert format
    upsert_data = [
        (v["id"], v["values"], v["metadata"])
        for v in vectors
    ]

    # Split into batches
    batches = [
        upsert_data[i:i + batch_limit]
        for i in range(0, len(upsert_data), batch_limit)
    ]

    # If only one batch, upsert directly
    if len(batches) == 1:
        index.upsert(vectors=batches[0])
        return

    # Parallel upserts for multiple batches
    def upsert_batch(batch):
        index.upsert(vectors=batch)

    with ThreadPoolExecutor(max_workers=min(4, len(batches))) as executor:
        list(executor.map(upsert_batch, batches))
