from openai import OpenAI
from prompt import generate_prompt

client = OpenAI()

def answer_generation(chunk: str, question: str):
    try:
        prompt = generate_prompt(question, chunk)
        response = client.chat.completions.create(
            model="gpt-5o-mini", # You can use other models like gpt-4o, etc.
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=0.7, # Controls the randomness of the output
            max_tokens=1000, # The maximum number of tokens to generate
        )
        
        print(response.choices[0].message.content)

    except Exception as e:
        print(f"An error occurred: {e}")