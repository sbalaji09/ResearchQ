from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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