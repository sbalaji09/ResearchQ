def generate_system_prompt(metadata: dict = None):
    """Generate the system prompt with instructions for the assistant."""
    doc_info = ""
    if metadata:
        doc_id = metadata.get('document_id', 'Unknown Document')
        sections = metadata.get('sections', [])
        doc_info = f"Document: {doc_id}\nSections referenced: {', '.join(set(sections))}"

    prompt = f"""You are a careful research assistant answering questions about an academic paper.

Document Information:
{doc_info}

Your task:
- You will receive text chunks from a research paper and a specific question.
- Your ONLY task is to answer the user's specific question. Do NOT provide a general summary.
- Focus exclusively on what the question asks. For example, if the question asks what students did NOT use devices for, answer ONLY that.
- Use ONLY information from the provided text chunks. Do not use external knowledge.
- If the chunks do not contain enough information to answer the question, say exactly:
  "The provided text does not contain specific information about [topic]."

Answering rules:
- Do NOT include headings, section titles, labels, or words like "Analysis", "Analytics", "Summary", "Explanation" as standalone headings in your answer.
- Do NOT mention the context, chunks, or that you are analyzing a document.
- Start by directly answering the question in plain language.
- Be concise and direct. Avoid long introductions or unrelated background.
- If the question has multiple parts, answer each part clearly.
- When relevant, you may mention the section name in parentheses, e.g. (Results), using the section names from the text."""

    return prompt

# generate the user prompt with the question and context
def generate_user_prompt(chunks_text: str, question: str):
    prompt = f"""Here is context from a research paper:

{chunks_text}

Question:
{question}

Instructions:
Answer ONLY this specific question using the information in the context above.
Do not provide a general summary of the study.
Do not add headings or section titles in your answer.
Respond in plain prose."""
    return prompt