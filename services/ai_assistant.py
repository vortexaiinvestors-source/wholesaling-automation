import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_ai(question: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a deal-finding assistant for VortexAI."},
            {"role": "user", "content": question}
        ]
    )

    return response["choices"][0]["message"]["content"]
