from dotenv import load_dotenv
from openai import OpenAI
import os
from pathlib import Path

from prompt import generate_system_prompt, generate_user_prompt

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

        # Build document info for citation
        doc_info = ""
        if metadata:
            doc_id = metadata.get('document_id', 'Unknown Document')
            section_list = metadata.get('sections', [])
            doc_info = f"Document: {doc_id}\nSections referenced: {', '.join(set(section_list))}"

        system_prompt = generate_system_prompt(chunks_text, metadata)
        user_prompt = generate_user_prompt(chunks_text, metadata)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_completion_tokens=800,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"An error occurred: {e}")
        return None