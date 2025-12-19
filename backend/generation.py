import re
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
        # Format chunks with chunk numbers (all from same document)
        formatted_chunks = []
        sections = metadata.get('sections', [])
        documents = metadata.get('documents', [])

        citations = []

        for i, chunk in enumerate(chunks):
            section = sections[i] if i < len(sections) else 'Unknown'
            doc_id = documents[i] if i < len(documents) else (documents[0] if documents else 'Unknown')

            citation_id = i + 1
            citations.append({
                "id": citation_id,
                "document": doc_id,
                "section": section,
                "text": chunk
            })

            formatted_chunks.append(f"[{citation_id}] (Document: {doc_id}, Section: {section})\n{chunk}")

        chunks_text = "\n\n---\n\n".join(formatted_chunks)

        # Generate prompts
        system_prompt = generate_system_prompt(metadata)
        user_prompt = generate_user_prompt(chunks_text, question)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_completion_tokens=800,
        )

        answer_text = response.choices[0].message.content
        answer_text = validate_citations(answer_text, len(chunks))

        return {
            "answer": answer_text,
            "citations": citations,
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def format_chunks_for_prompts(chunks: list[str], metadata: dict) -> str:
    formatted = []
    for i, chunk in enumerate(chunks):
        section = metadata["sections"][i] if i < len(metadata["sections"]) else "Unknown"
        doc_id = metadata.get("documents", ["unknown"])[0]

        formatted.append(f"[Document: {doc_id}, Section: {section}]\n{chunk}")
    
    return "\n\n---\n\n".join(formatted)

# validates that citation numbers in the answer are valid and removes or flags invalid citations
def validate_citations(answer: str, max_citation: int) -> str:
    citation_pattern = r'\[(\d+)\]'

    def replace_invalid(match):
        citation_num = int(match.group(1))
        if 1 <= citation_num <= max_citation:
            return match.group(0)
        else:
            return ""
    
    validated = re.sub(citation_pattern, replace_invalid, answer)
    return validated