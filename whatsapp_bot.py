from flask import Flask, request
import requests
from gemini_utils import generate_with_gemini
from ollama_utils import ask_ollama

app = Flask(__name__)

# === Configuration ===
VERIFY_TOKEN = "Token"
WHATSAPP_TOKEN = "whatsapptoken"
PHONE_NUMBER_ID = "numberid"

# === In-memory session store ===
session_memory = {}  # user_id -> list of message dicts
user_models = {}     # user_id -> model choice

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
            message = entry["messages"][0]
            phone = message["from"]
            msg_type = message["type"]

            # === Button reply handling ===
            if msg_type == "interactive":
                reply_id = message["interactive"]["button_reply"]["id"]

                if reply_id == "model_gemini":
                    user_models[phone] = "gemini"
                    send_whatsapp_message(phone, "✅ Model set to Gemini. Ask your legal question.")
                    return "ok", 200

                elif reply_id == "model_ollama":
                    user_models[phone] = "ollama"
                    send_whatsapp_message(phone, "✅ Model set to Ollama. Ask your legal question.")
                    return "ok", 200

                elif reply_id == "reset_memory":
                    session_memory[phone] = []
                    send_whatsapp_message(phone, "🧠 Memory reset. Please select a model again.")
                    send_model_selection_buttons(phone)
                    return "ok", 200

            # === Text handling ===
            elif msg_type == "text":
                msg = message["text"]["body"].strip()

                if phone not in user_models:
                    send_model_selection_buttons(phone)
                    return "ok", 200

                # Generate AI response
                history = session_memory.setdefault(phone, [])
                history.append({"role": "user", "content": msg})
                context = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history[-4:])
                model_choice = user_models.get(phone, "gemini")

                if model_choice == "gemini":
                    reply = generate_with_gemini(prompt=msg, context=context)
                else:
                    reply = ask_ollama(msg, context=context)

                history.append({"role": "bot", "content": reply})
                send_whatsapp_message(phone, reply)

                # After sending response, show options again
                send_post_response_buttons(phone)

    except Exception as e:
        print("❌ Error handling message:", e)

    return "ok", 200

# === Send plain text message ===
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
    requests.post(url, headers=headers, json=payload)

# === Show initial model selection ===
def send_model_selection_buttons(recipient_id):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "👋 Hello! Choose a model to begin:"},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "model_gemini", "title": "Gemini"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "model_ollama", "title": "Ollama"}
                    }
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

# === Show Gemini, Ollama, Reset options after each response ===
def send_post_response_buttons(recipient_id):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "🔁 Would you like to switch models or reset memory?"},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "model_gemini", "title": "Gemini"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "model_ollama", "title": "Ollama"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "reset_memory", "title": "🧠 Reset"}
                    }
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    app.run(port=5500)
