import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

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

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3.2:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 120}
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        # Fallback rule-based reason if LLM unavailable
        if score < 0.3:
            return f"Attachment ({file_type}) contains no significant phishing signals."
        parts = []
        if any("credential" in f for f in flags):
            parts.append("requests or exposes sensitive credentials")
        if any("suspicious_urls" in f for f in flags):
            parts.append("contains suspicious verification/login URLs")
        if any("keyword" in f for f in flags):
            parts.append("uses known phishing language patterns")
        return f"This {file_type} attachment " + "; ".join(parts) + "." if parts else f"Risk score: {score}."