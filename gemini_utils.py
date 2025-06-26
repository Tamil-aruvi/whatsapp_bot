# gemini_utils.py

import google.generativeai as genai

# ✅ Configure Gemini API with your API key (can be set directly or via environment variable)
GOOGLE_API_KEY = "key"  # Replace with os.getenv("GOOGLE_API_KEY") for production
genai.configure(api_key=GOOGLE_API_KEY)

# ✅ Initialize Gemini model (you can switch to gemini-pro or others if needed)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# ✅ Function to generate reply with optional context
def generate_with_gemini(prompt: str, context: str = "") -> str:
    full_prompt = f"{context}\n\n{prompt}" if context else prompt
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"[Gemini Error]: {str(e)}"
