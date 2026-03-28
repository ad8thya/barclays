import ollama


def generate_llm_reason(text: str, flags: list[str], score: float, file_type: str) -> str:
    prompt = f"""
You are a cybersecurity analysis engine.

Your task is to generate a concise, objective explanation.

Rules:
- Do NOT use first-person language.
- Do NOT speculate.
- Do NOT assume phishing if no evidence.
- Be direct and factual.
- Max 2 sentences.

Input:
File type: {file_type}
Flags: {flags}
Risk score: {score}
Content: {text[:300]}

Output:
"""

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"].strip()