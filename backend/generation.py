from openai import OpenAI
import os
from prompt import generate_prompt

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def answer_generation(chunks: list[str], question: str):
    try:
        prompt = generate_prompt(question, chunks)
        response = client.chat.completions.create(
            model="gpt-5-mini", # You can use other models like gpt-4o, etc.
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "context": chunks, "question": question},
            ],
            temperature=0.7, # Controls the randomness of the output
            max_tokens=1000, # The maximum number of tokens to generate
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"An error occurred: {e}")