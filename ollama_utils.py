# ollama_utils.py

from langchain_ollama.llms import OllamaLLM

# Load Ollama model (phi3 must be available locally)
llm = OllamaLLM(model="phi3:mini")

def ask_ollama(query, context=None):
    if context:
        prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
    else:
        prompt = f"Question: {query}\n\nAnswer:"

    try:
        return llm.invoke(prompt)
    except Exception as e:
        return f"[Ollama Error]: {e}"
