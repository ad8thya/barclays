from services.llm_service import analyze_with_llm

def analyze_js_semantics(js_snippets: list):
    if not js_snippets:
        return "No JavaScript content to analyze"

    combined_js = "\n\n".join(js_snippets[:2])  # limit

    prompt_features = {
        "js_code": combined_js
    }

    try:
        response = analyze_with_llm(prompt_features)
        return response
    except Exception as e:
        print("JS LLM ERROR:", e)
        return "JS analysis failed"