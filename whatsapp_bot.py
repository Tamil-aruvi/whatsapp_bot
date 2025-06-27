from flask import Flask, request, jsonify
import requests
import os
from gemini_utils import generate_with_gemini
from ollama_utils import ask_ollama

app = Flask(__name__)

# === Configuration ===
VERIFY_TOKEN = "verify token"
WHATSAPP_TOKEN = "token"
PHONE_NUMBER_ID = "num"

# === In-memory session store ===
session_memory = {}  # user_id -> list of message dicts
user_models = {}     # user_id -> model choice ("gemini" or "ollama")

@app.route("/", methods=["GET"], endpoint="verify")
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Unauthorized", 403

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    print("📩 Incoming data:", data)

    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            phone = entry["messages"][0]["from"]
            msg = entry["messages"][0]["text"]["body"].strip().lower()

            print(f"✅ Message entry found\n📱 From: {phone} | Message: {msg}")

            # ✅ Model switch
            if msg.startswith("/model"):
                model_choice = msg.split(" ")[-1]
                if model_choice in ["gemini", "ollama"]:
                    user_models[phone] = model_choice
                    send_whatsapp_message(phone, f"✅ Model changed to: {model_choice.capitalize()}")
                else:
                    send_whatsapp_message(phone, "❌ Invalid model. Use: /model gemini or /model ollama")
                return "ok", 200

            # ✅ RESET handling
            if msg in ["/reset", "reset", "clear"]:
                session_memory[phone] = []
                send_whatsapp_message(phone, "🧠 Memory reset. Start a new legal query.")
                return "ok", 200

            # Normal flow
            history = session_memory.setdefault(phone, [])
            history.append({"role": "user", "content": msg})
            formatted = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history[-4:])

            model_choice = user_models.get(phone, "gemini")
            if model_choice == "gemini":
                reply_text = generate_with_gemini(prompt=msg, context=formatted)
            else:
                reply_text = ask_ollama(msg, context=formatted)

            history.append({"role": "bot", "content": reply_text})
            send_whatsapp_message(phone, reply_text)

    except Exception as e:
        print("❌ Error handling message:", e)

    return "ok", 200

def send_whatsapp_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message_text}
    }
    r = requests.post(url, headers=headers, json=payload)
    print("📤 Sent:", r.status_code, r.text)

if __name__ == "__main__":
    app.run(port=5500)
