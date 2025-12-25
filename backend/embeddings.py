# calls embedding provider to convert text chunks into embeddings where each vector is stored in Pinecone with metadata
import os
from pinecone import Pinecone
from dotenv import load_dotenv
from pathlib import Path
from llm_provider import get_embedding as provider_get_embedding, get_embeddings_batch

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# gets the embedding for one piece of text
def get_embedding(text: str):
    return provider_get_embedding(text)

# embeds chunks of data using the configured embedding provider
def embed_chunks(chunks: list[str], metadata: list[dict], batch_size: int = 64):
    if len(chunks) != len(metadata):
        return

    vectors = []

    for start in range(0, len(chunks), batch_size):
        end = min(start+batch_size, len(chunks))
        batch_chunks = chunks[start: end]
        batch_metadata = metadata[start:end]

        batch_embeddings = get_embeddings_batch(batch_chunks)

        for embedding, meta in zip(batch_embeddings, batch_metadata):
            vector_id = f"{meta['pdf_id']}_chunk_{meta['chunk_index']}"
            vectors.append({"id": vector_id, "values": embedding, "metadata": meta})

    return vectors

# stores vectors in pinecone based on a batch limit
def store_in_pinecone(vectors, batch_limit=100):
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    index = pc.Index(index_name)

    upsert_data = []
    for vector_data in vectors:
        upsert_data.append(
            (vector_data["id"], vector_data["values"], vector_data["metadata"])
        )

        if len(upsert_data) >= batch_limit:
            index.upsert(vectors=upsert_data)
            upsert_data = []

    if upsert_data:    
        index.upsert(vectors=upsert_data)
