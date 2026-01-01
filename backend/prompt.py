def generate_system_prompt(metadata: dict = None, conversation_history: list = None):
    """Generate the system prompt with instructions for the assistant."""
    doc_info = ""
    conversation_instruction = ""
    cross_doc_instruction = ""

    if metadata:
        documents = metadata.get('documents', [])
        sections = metadata.get('sections', [])
        unique_docs = list(set(documents))

        if documents:
            doc_info = f"Documents: {', '.join(set(documents))}\nSections referenced: {', '.join(set(sections))}"

        if len(unique_docs) > 1:
            cross_doc_instruction = """
Cross-document analysis:
- You are analyzing multiple research papers.
- When comparing across documents, clearly identify which document each piece of information comes from.
- Use format: "In Document A... while in Document B..." for comparisons.
- Note similarities and differences between the papers when relevant.
- Always specify the document name when citing: "According to [Document Name] [1]..."
"""

    if conversation_history and len(conversation_history) > 0:
        conversation_instruction = """
        Conversation context:
        - This is a follow-up question in an ongoing conversation.
        - Consider the previous questions and answers when responding.
        - If the user refers to something mentioned before (e.g., "it", "they", "that method"), 
        use the conversation context to understand what they mean.
        - You can reference your previous answers if relevant.
        """

    prompt = f"""You are a careful research assistant answering questions about an academic paper.

Document Information:
{doc_info}
{cross_doc_instruction}
{conversation_instruction}
Your task:
- You will receive text chunks from a research paper and a specific question.
- Your ONLY task is to answer the user's specific question. Do NOT provide a general summary.
- Focus exclusively on what the question asks. For example, if the question asks what students did NOT use devices for, answer ONLY that.
- Use ONLY information from the provided text chunks. Do not use external knowledge.
- If the chunks do not contain enough information to answer the question, say exactly:
  "The provided text does not contain specific information about [topic]."

Quantitative data requirement (CRITICAL):
- ALWAYS include specific numbers, percentages, statistics, p-values, sample sizes, and measurements from the text.
- If the chunks contain quantitative results (e.g., "85% of participants", "n=120", "p<0.05", "mean=3.4"), you MUST include them in your answer.
- Never give a vague answer when specific numbers exist in the source material.
- Example BAD: "Most students preferred mobile learning."
- Example GOOD: "85% of students (n=120) preferred mobile learning [1]."
- If comparing results, include the specific values: "Group A scored 78.3% vs Group B at 62.1% (p<0.01) [2]."

Citation rules (IMPORTANT):
- Each chunk is labeled with a number like [1], [2], etc.
- When you use information from a chunk, cite it using the number in square brackets.
- Place citations at the end of the sentence or claim, before the period.
- Example: "The study found that 85% of students preferred mobile learning [1]."
- Example: "Multiple studies support this finding [1][3]."
- You MUST cite sources for all factual claims from the documents.
- If combining information from multiple chunks, cite all relevant sources.

Formatting rules:
- Do NOT include headings like "Summary" or "Analysis" in your answer.
- Do NOT mention "chunks" or "context" - just answer naturally with citations.
- Be concise and direct.
- Start by directly answering the question."""

    return prompt

# generate the user prompt with the question and context
def generate_user_prompt(chunks_text: str, question: str, conversation_history: list = None):
    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        history_parts = []
        for msg in conversation_history:
            role_label = "User" if msg["role"] == "user" else "Assistant"

            content = msg["content"]
            if len(content) > 300:
                content = content[:300] + "..."
            history_parts.append(f"{role_label}: {content}")
        
        history_text = f"""
        Previous conversation:
        ---
        {chr(10).join(history_parts)}
        ---

        """
    prompt = f"""{history_text}Here are numbered excerpts from research papers:

{chunks_text}

Question: {question}

Answer the question using the excerpts above. If this is a follow-up question, use the conversation context to understand what the user is asking about. Cite sources using [1], [2], etc.

IMPORTANT: Include ALL quantitative data (numbers, percentages, p-values, sample sizes) from the excerpts. Never summarize with vague terms like "many" or "most" when specific numbers are available."""
    return prompt