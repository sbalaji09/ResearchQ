from dotenv import load_dotenv
from openai import OpenAI
import os
from prompt import generate_prompt
from pathlib import Path
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def answer_generation(chunks: list[str], question: str, metadata: dict):
    try:
        # Format chunks with section labels for better citations
        formatted_chunks = []
        sections = metadata.get('sections', [])

        for i, chunk in enumerate(chunks):
            section = sections[i] if i < len(sections) else 'Unknown'
            formatted_chunks.append(f"[Source {i+1} - {section} Section]\n{chunk}")

        chunks_text = "\n\n---\n\n".join(formatted_chunks)
        prompt = generate_prompt(chunks_text, metadata)
        response = client.chat.completions.create(
            model="gpt-5-mini", # You can use other models like gpt-4o, etc.
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.2, # Controls the randomness of the output
            max_tokens=1000, # The maximum number of tokens to generate
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"An error occurred: {e}")
        return None