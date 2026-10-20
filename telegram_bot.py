
import os
import json
import hmac
import requests
from flask import Flask, request, abort, jsonify
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
OWNER_ID = os.environ.get("TELEGRAM_OWNER_ID", "")

application = Application.builder().token(BOT_TOKEN).build()

MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Process File 📤"),
         KeyboardButton("Vip Status 🛏")],
        [KeyboardButton("Vip Shop 🛒"),
         KeyboardButton("GitHub Status 📊")],
        [KeyboardButton("Scheduled Files ⚙️"),
         KeyboardButton("Help 🆘")],
        [KeyboardButton("API 1 🔌"),
         KeyboardButton("API 2 🔌")],
        [KeyboardButton("API 3 🔌"),
         KeyboardButton("API 4 🔌")],
        [KeyboardButton("API 5 🔌"),
         KeyboardButton("Cancel ❌")],
    ],
    resize_keyboard=True,
)

@app.get("/")
def home():
    return "SILENT GMR JWT BOT is running!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        return
    await update.message.reply_text(
        "Welcome to SILENT GMR JWT BOT!\nChoose an option below.",
        reply_markup=MENU,
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        return

    text = update.message.text

    if text == "Process File 📤":
        context.user_data["waiting_json"] = True
        await update.message.reply_text(
            'Ab .json file bhejo. Expected format:\n\n'
            '[{"uid":"user1","password":"pass1"}]\n\n'
            "File sirf structure validation ke liye process hogi."
        )
    elif text == "Cancel ❌":
        context.user_data.pop("waiting_json", None)
        await update.message.reply_text("Operation cancelled.", reply_markup=MENU)
    elif text == "Vip Status 🛏":
        await update.message.reply_text("VIP status: Demo mode.")
    elif text == "Vip Shop 🛒":
        await update.message.reply_text("VIP shop: Demo mode.")
    elif text == "GitHub Status 📊":
        await update.message.reply_text("GitHub status: Not configured.")
    elif text == "Scheduled Files ⚙️":
        await update.message.reply_text("No scheduled files configured.")
    elif text == "Help 🆘":
        await update.message.reply_text(
            "Use Process File 📤 to validate a JSON file."
        )
    elif text.startswith("API "):
        await update.message.reply_text(
            "API integration is not configured yet."
        )

async def json_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != OWNER_ID:
        return
    if not context.user_data.get("waiting_json"):
        return

    document = update.message.document
    if not document or not document.file_name.lower().endswith(".json"):
        await update.message.reply_text("Please send a .json document.")
        return

    if document.file_size and document.file_size > 1_000_000:
        await update.message.reply_text("File too large. Maximum size: 1 MB.")
        return

    tg_file = await context.bot.get_file(document.file_id)
    raw = await tg_file.download_as_bytearray()

    try:
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, list):
            raise ValueError("Top level must be a JSON list.")
        valid = 0
        invalid = 0
        for item in data:
            if (
                isinstance(item, dict)
                and isinstance(item.get("uid"), str)
                and item["uid"].strip()
                and isinstance(item.get("password"), str)
                and item["password"]
            ):
                valid += 1
            else:
                invalid += 1

        context.user_data.pop("waiting_json", None)
        await update.message.reply_text(
            "JSON validation complete ✅\n"
            f"Total entries: {len(data)}\n"
            f"Valid structure: {valid}\n"
            f"Invalid structure: {invalid}\n"
            "Passwords were not used or saved.",
            reply_markup=MENU,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        await update.message.reply_text(
            "Invalid JSON. Please send a JSON list of objects."
        )

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", start))
application.add_handler(
    MessageHandler(filters.Document.ALL, json_handler)
)
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)
)

@app.post("/webhook")
def webhook():
    if not WEBHOOK_SECRET:
        abort(500)
    supplied = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )
    if not hmac.compare_digest(supplied, WEBHOOK_SECRET):
        abort(403)

    payload = request.get_json(silent=True) or {}
    try:
        import asyncio
        asyncio.run(application.initialize())
        asyncio.run(application.process_update(Update.de_json(payload, application.bot)))
    except Exception:
        app.logger.exception("Update processing failed")
        return jsonify({"ok": False}), 500
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
    )
