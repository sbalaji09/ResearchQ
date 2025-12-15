def generate_prompt(question: str, text_chunk: str):
    prompt = f"""
        You are an expert research assistant. You will receive:
        1. A question.
        2. A chunk of text that definitely contains the answer.

        Your task:
        - Answer the question **using only** the information in the text_chunk.
        - Do **not** use external knowledge.
        - If the chunk partially answers the question, answer only what can be supported by the text.
        - Quote or reference specific phrases when useful.
        - Be concise, accurate, and avoid speculation.
        - Use only the information from the provided context to answer the given question
        - Cite your sources in standard MLA-8 format whenever needed

        --------------------
        TEXT CHUNK:
        {text_chunk}

        QUESTION:
        {question}

        --------------------
        FINAL INSTRUCTIONS:
        Provide a clear, well-written answer using only the chunk above.
        If the answer cannot be fully determined from the text, state which parts are unclear.
    """
    return prompt
