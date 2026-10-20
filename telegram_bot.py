
import os
import json
import hmac
import requests
from flask import Flask, request, abort, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
OWNER_ID = os.environ.get("TELEGRAM_OWNER_ID", "")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
MAX_FILE_SIZE = 1_000_000

MENU = {
    "keyboard": [
        [{"text": "Process File 📤"}, {"text": "Vip Status 🛏"}],
        [{"text": "Vip Shop 🛒"}, {"text": "GitHub Status 📊"}],
        [{"text": "Scheduled Files ⚙️"}, {"text": "Help 🆘"}],
        [{"text": "API 1 🔌"}, {"text": "API 2 🔌"}],
        [{"text": "API 3 🔌"}, {"text": "API 4 🔌"}],
        [{"text": "API 5 🔌"}, {"text": "Cancel ❌"}],
    ],
    "resize_keyboard": True,
}

def send_message(chat_id, text, keyboard=True):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = MENU
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=15,
        ).raise_for_status()
    except requests.RequestException:
        app.logger.exception("Failed to send Telegram message")

@app.get("/")
def home():
    return "SILENT GMR JWT BOT is running!"

def validate_json_file(document):
    if not document.get("file_name", "").lower().endswith(".json"):
        return "Please send a .json file."

    size = document.get("file_size", 0)
    if size and size > MAX_FILE_SIZE:
        return "File too large. Maximum size is 1 MB."

    info = requests.get(
        f"{TELEGRAM_API}/getFile",
        params={"file_id": document["file_id"]},
        timeout=15,
    ).json()

    if not info.get("ok"):
        return "Could not download the file. Please try again."

    file_path = info["result"]["file_path"]
    download_url = (
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    )
    response = requests.get(download_url, timeout=20)
    response.raise_for_status()

    if len(response.content) > MAX_FILE_SIZE:
        return "File too large. Maximum size is 1 MB."

    data = json.loads(response.content.decode("utf-8"))

    if not isinstance(data, list):
        return "Invalid format: the JSON top level must be a list."

    valid = 0
    invalid = 0

    for item in data:
        if (
            isinstance(item, dict)
            and isinstance(item.get("uid"), str)
            and bool(item["uid"].strip())
            and isinstance(item.get("password"), str)
            and bool(item["password"])
        ):
            valid += 1
        else:
            invalid += 1

    return (
        "JSON validation complete ✅\n"
        f"Total entries: {len(data)}\n"
        f"Valid structure: {valid}\n"
        f"Invalid structure: {invalid}\n\n"
        "Passwords were not used or saved."
    )

@app.post("/webhook")
def webhook():
    if not BOT_TOKEN or not WEBHOOK_SECRET:
        abort(500)

    supplied = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )
    if not hmac.compare_digest(supplied, WEBHOOK_SECRET):
        abort(403)

    update = request.get_json(silent=True) or {}
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    user = message.get("from") or {}

    chat_id = chat.get("id")
    user_id = str(user.get("id", ""))

    if not chat_id:
        return jsonify({"ok": True})

    # Owner-only bot
    if not OWNER_ID or user_id != OWNER_ID:
        return jsonify({"ok": True})

    try:
        document = message.get("document")
        if document:
            result = validate_json_file(document)
            send_message(chat_id, result)
            return jsonify({"ok": True})

        text = (message.get("text") or "").strip()

        if text in ("/start", "/help", "Help 🆘"):
            reply = (
                "Welcome to SILENT GMR JWT BOT!\n\n"
                "Process File 📤 - Validate a JSON file\n"
                "Vip Status 🛏 - Demo status\n"
                "Vip Shop 🛒 - Demo shop\n"
                "GitHub Status 📊 - Demo status\n"
                "Scheduled Files ⚙️ - Demo status\n"
                "API 1–5 🔌 - Not configured\n"
                "Cancel ❌ - Cancel current operation"
            )
        elif text == "Process File 📤":
            reply = (
                "Ab apni .json file bhejo.\n"
                'Format: [{"uid":"user1","password":"pass1"}]\n'
                "File sirf validation ke liye check hogi."
            )
        elif text == "Cancel ❌":
            reply = "Cancelled. Koi file process nahi hui."
        elif text in ("/status", "Vip Status 🛏"):
            reply = "Bot service is running. ✅"
        elif text == "Vip Shop 🛒":
            reply = "VIP Shop demo mode mein hai."
        elif text == "GitHub Status 📊":
            reply = "GitHub integration configured nahi hai."
        elif text == "Scheduled Files ⚙️":
            reply = "Scheduled file processing configured nahi hai."
        elif text.startswith("API "):
            reply = "Ye API abhi configure nahi hai."
        else:
            reply = "Command samajh nahi aaya. Help 🆘 dabao."

        send_message(chat_id, reply)
    except (
        requests.RequestException,
        ValueError,
        UnicodeDecodeError,
        KeyError,
    ):
        app.logger.exception("Webhook processing failed")
        send_message(chat_id, "File process nahi hui. Format check karo.")

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
