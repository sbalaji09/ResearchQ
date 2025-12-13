from openai import OpenAI
import os
from pinecone import Pinecone, ServerlessSpec

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# gets the embedding for one piece of text
def get_embedding(text: str):
    cleaned_text = text.strip()
    if not cleaned_text:
        return []
    
    response = client.embeddings.create(
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

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=batch_chunks
        )
        batch_embeddings = [item.embedding for item in response.data]

        for i, (embedding, metadata) in enumerate(zip(batch_embeddings, batch_metadata)):
            vector_id = f"{metadata['pdf_id']}_chunk_{metadata['chunk_index']}"

            vectors.append({"id": vector_id, "values": embedding, "metadata": metadata})

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
