
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
TIMEOUT = 15

# Render Environment mein actual API URLs set karo.
API_URLS = {
    "API 1 🔌": os.environ.get("API_1_URL", "https://jwt-bot-rule.onrender.com"),
    "API 2 🔌": os.environ.get("API_2_URL", ""),
    "API 3 🔌": os.environ.get("API_3_URL", ""),
    "API 4 🔌": os.environ.get("API_4_URL", ""),
    "API 5 🔌": os.environ.get("API_5_URL", ""),
}

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
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            app.logger.error("Telegram sendMessage failed")
    except requests.RequestException:
        app.logger.exception("Telegram message failed")

def call_configured_api(chat_id, button_text):
    url = API_URLS.get(button_text, "").strip()

    if not url:
        send_message(
            chat_id,
            f"{button_text}\n\nAPI URL configured nahi hai.\n"
            "Render → Environment mein iska URL add karo."
        )
        return

    # Sirf configured endpoint ko GET request bhejo.
    # Koi password ya Telegram token API ko forward nahi hota.
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type.lower():
            try:
                data = response.json()
                output = json.dumps(data, ensure_ascii=False)
            except ValueError:
                output = "API ne invalid JSON return kiya."
        else:
            output = response.text

        # Telegram message length limit ke andar rakho.
        if len(output) > 3500:
            output = output[:3500] + "\n\n...Response shortened."

        send_message(chat_id, f"{button_text} response:\n\n{output}")

    except requests.Timeout:
        send_message(chat_id, "API request timeout ho gayi.")
    except requests.RequestException:
        app.logger.exception("Configured API request failed")
        send_message(
            chat_id,
            "API request fail hui. URL, access aur API status check karo."
        )

@app.get("/")
def home():
    return "SILENT GMR JWT BOT is running!", 200

def validate_json_file(document):
    filename = document.get("file_name", "")

    if not filename.lower().endswith(".json"):
        return "Please .json file bhejo."

    size = document.get("file_size", 0)
    if size and size > MAX_FILE_SIZE:
        return "File too large. Maximum size 1 MB hai."

    info_response = requests.get(
        f"{TELEGRAM_API}/getFile",
        params={"file_id": document["file_id"]},
        timeout=TIMEOUT,
    )
    info_response.raise_for_status()
    info = info_response.json()

    if not info.get("ok"):
        return "File download nahi ho saki."

    file_path = info["result"]["file_path"]
    download_url = (
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    )
    response = requests.get(download_url, timeout=TIMEOUT)
    response.raise_for_status()

    if len(response.content) > MAX_FILE_SIZE:
        return "File too large. Maximum size 1 MB hai."

    data = json.loads(response.content.decode("utf-8"))

    if not isinstance(data, list):
        return "Invalid JSON format: top level par list honi chahiye."

    valid = 0
    invalid = 0

    for item in data:
        if not isinstance(item, dict):
            invalid += 1
            continue

        # Generic JSON structure validation.
        # Credential values ko log ya display nahi kiya jata.
        uid = item.get("uid")
        password = item.get("password")

        if (
            isinstance(uid, str) and uid.strip()
            and isinstance(password, str) and password
        ):
            valid += 1
        else:
            invalid += 1

    return (
        "JSON validation complete ✅\n"
        f"Total entries: {len(data)}\n"
        f"Valid structure: {valid}\n"
        f"Invalid structure: {invalid}\n\n"
        "File ka content save nahi kiya gaya."
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

    # Owner-only access.
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
                "Process File 📤 - JSON validation\n"
                "Vip Status 🛏 - Service status\n"
                "Vip Shop 🛒 - Demo shop\n"
                "GitHub Status 📊 - GitHub status\n"
                "Scheduled Files ⚙️ - Scheduling status\n"
                "API 1–5 🔌 - Configured API endpoint\n"
                "Cancel ❌ - Cancel message"
            )
            send_message(chat_id, reply)

        elif text == "Process File 📤":
            send_message(
                chat_id,
                "Ab apni .json file bhejo (maximum 1 MB).\n"
                'Expected format: [{"uid":"example","password":"example"}]\n'
                "Real passwords use karne ke bajay test data use karo."
            )

        elif text == "Cancel ❌":
            send_message(chat_id, "Cancelled. ✅")

        elif text in ("/status", "Vip Status 🛏"):
            send_message(chat_id, "Bot service is running. ✅")

        elif text == "Vip Shop 🛒":
            send_message(chat_id, "VIP Shop abhi demo mode mein hai.")

        elif text == "GitHub Status 📊":
            send_message(
                chat_id,
                "GitHub integration abhi configured nahi hai."
            )

        elif text == "Scheduled Files ⚙️":
            send_message(
                chat_id,
                "Scheduled processing abhi configured nahi hai."
            )

        elif text in API_URLS:
            call_configured_api(chat_id, text)

        else:
            send_message(chat_id, "Command samajh nahi aaya. Help 🆘 dabao.")

    except (
        requests.RequestException,
        ValueError,
        UnicodeDecodeError,
        KeyError,
    ):
        app.logger.exception("Webhook processing failed")
        send_message(
            chat_id,
            "Request/file process nahi hui. URL ya JSON format check karo."
        )

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
