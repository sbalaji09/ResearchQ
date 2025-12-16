def generate_system_prompt(metadata: dict = None):
    """Generate the system prompt with instructions for the assistant."""
    doc_info = ""
    if metadata:
        doc_id = metadata.get('document_id', 'Unknown Document')
        sections = metadata.get('sections', [])
        doc_info = f"Document: {doc_id}\nSections referenced: {', '.join(set(sections))}"

    prompt = f"""You are an expert research assistant specialized in analyzing academic papers.

Document Information:
{doc_info}

CRITICAL INSTRUCTIONS:
1. You will receive text chunks from a research paper and a specific question.
2. Your ONLY task is to answer the user's SPECIFIC question - do NOT provide a general summary.
3. Focus EXCLUSIVELY on what the question asks. If the question asks about "what students did NOT use devices for", answer ONLY that.
4. Use ONLY information from the provided text chunks. Do not use external knowledge.
5. If the chunks don't contain information to answer the question, say "The provided text does not contain specific information about [topic]."
6. Quote or paraphrase specific passages that directly answer the question.
7. Cite using format: (Section Name) - all chunks are from the same document, so just reference the section.
8. Be concise and direct. Avoid lengthy introductions or tangential information.

ANSWERING STYLE:
- Start by directly addressing what the question asks
- Do NOT begin with general background about the study
- Do NOT summarize the entire study - only answer what was asked
- If the question has multiple parts, address each part specifically"""

    return prompt


def generate_user_prompt(chunks_text: str, question: str):
    """Generate the user prompt with the question and context."""
    prompt = f"""CONTEXT FROM RESEARCH PAPER:
{chunks_text}

---

QUESTION: {question}

Remember: Answer ONLY this specific question. Do not provide a general summary of the study. Focus directly on what is being asked."""

    return prompt
