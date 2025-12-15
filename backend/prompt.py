def generate_prompt(text_chunks: str, metadata: dict = None):
    # Build document info for citation
    doc_info = ""
    if metadata:
        doc_id = metadata.get('document_id', 'Unknown Document')
        sections = metadata.get('sections', [])
        doc_info = f"Document: {doc_id}\nSections referenced: {', '.join(set(sections))}"

    prompt = f"""
        You are an expert research assistant. You will receive:
        1. A question from the user.
        2. Multiple text chunks from a research paper, each labeled with its source section.

        Document Information:
        {doc_info}

        Your task:
        - Answer the question **using only** the information in the provided text chunks.
        - Do **not** use external knowledge.
        - If the chunks partially answer the question, answer only what can be supported by the text.
        - Quote or reference specific phrases when useful.
        - Be concise, accurate, and avoid speculation.
        - **Cite your sources** by referencing the source number and section (e.g., "According to Source 1 (Methods Section)...")

        --------------------
        TEXT CHUNKS:
        {text_chunks}

        --------------------
        FINAL INSTRUCTIONS:
        Provide a clear, well-written answer using only the chunks above.
        Include citations to the source numbers when making claims.
        If the answer cannot be fully determined from the text, state which parts are unclear.
    """
    return prompt
