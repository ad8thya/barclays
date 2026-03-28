import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def analyze_with_llm(features: dict):
    prompt = f"""
    You are a cybersecurity assistant.

    Analyze the following website features and determine if it is a phishing site.

    Features:
    {features}

    Return:
    1. Risk level (LOW, MEDIUM, HIGH)
    2. Short explanation (2-3 lines)
    """

    response = requests.post(OLLAMA_URL, json={
        "model": "llama3.2:latest",   # or llama3 (use your installed one)
        "prompt": prompt,
        "stream": False
    })

    return response.json()["response"]