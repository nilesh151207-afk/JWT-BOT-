
import os
import hmac
from flask import Flask, request, abort, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
OWNER_ID = os.environ.get("TELEGRAM_OWNER_ID", "")


@app.get("/")
def home():
    return "Telegram bot service is running!"


@app.post("/webhook")
def webhook():
    if not WEBHOOK_SECRET:
        abort(500)

    supplied_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if not hmac.compare_digest(supplied_secret, WEBHOOK_SECRET):
        abort(403)

    update = request.get_json(silent=True) or {}
    message = update.get("message", {})
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = str(user.get("id", ""))
    text = message.get("text", "")

    if not chat_id or not text:
        return jsonify({"ok": True})

    if user_id != OWNER_ID:
        return jsonify({"ok": True})

    if text == "/start":
        reply = "Bot online hai! Aapka owner access verify ho gaya."
    elif text == "/status":
        reply = "Bot service chal rahi hai."
    else:
        reply = "Commands: /start, /status"

    if BOT_TOKEN:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply},
            timeout=10,
        )

    return jsonify({"ok": True})
