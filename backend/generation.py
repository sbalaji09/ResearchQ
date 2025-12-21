import re
from dotenv import load_dotenv
from openai import OpenAI
import os
from pathlib import Path

from prompt import generate_system_prompt, generate_user_prompt
from cache import detect_query_complexity, get_model_for_complexity

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def answer_generation(chunks: list[str], question: str, metadata: dict, conversation_history: list = None) -> dict:
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
        system_prompt = generate_system_prompt(metadata, conversation_history)
        user_prompt = generate_user_prompt(chunks_text, question, conversation_history)

        messages = [{"role": "system", "content": system_prompt}]

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})
        
        complexity = detect_query_complexity(question)
        model_config = get_model_for_complexity(complexity)

        response = client.chat.completions.create(
            model=model_config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=model_config["temperature"],
            max_completion_tokens=model_config["max_tokens"],
        )

        answer_text = response.choices[0].message.content

        if not answer_text or not answer_text.strip():
            return {
                "answer": "I was unable to generate an answer from the available information.",
                "citations": citations,
                "error_code": "EMPTY_RESPONSE"
            }
        
        answer_text = validate_citations(answer_text, len(chunks))

        hallucination_check = detect_hallucination(answer_text, chunks)

        result = {
            "answer": answer_text,
            "citations": citations,
        }

        if hallucination_check["is_suspicious"]:
            result["hallucination_warning"] = hallucination_check["reason"]
            result["answer"] = f"Note: This answer may contain information not directly from the source documents.\n\n{answer_text}"
        
        return result

    except Exception as e:
        print(f"Generation error: {e}")
        return {
            "answer": "I encountered an error while generating the answer. Please try again.",
            "citations": [],
            "error": str(e),
            "error_code": "GENERATION_ERROR"
        }

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

# detect potential hallucinations by checking if key claims appear in chunks
def detect_hallucination(answer: str, chunks: list[str], threshold: float = 0.3) -> dict:
    suspicious_patterns = [
        r'\b(according to|as started|the (study|paper|research) (shows|found|states))\b.*?\.',
    ]

    total_chunk_length = sum(len(c) for c in chunks)
    if len(answer) > total_chunk_length * 1.5 and len(answer) > 500:
        return {
            "is_suspicious": True,
            "confidence": 0.6,
            "reason": "Answer is significantly longer than source material"
        }
    
    answer_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', answer))
    chunk_numbers = set()
    for chunk in chunks:
        chunk_numbers.update(re.findall(r'\b\d+(?:\.\d+)?%?\b', chunk))
    
    unsupported_numbers = answer_numbers - chunk_numbers
    unsupported_numbers = {n for n in unsupported_numbers if not (1900 <= int(re.sub(r'[^\d]', '', n) or 0) <= 2030)}

    if len(unsupported_numbers) > 2:
        return {
            "is_suspicious": True,
            "confidence": 0.7,
            "reason": f"Answer contains numbers not found in source: {unsupported_numbers}"
        }

    return {
        "is_suspicious": False,
        "confidence": 0.9,
        "reason": None
    }