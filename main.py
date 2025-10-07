import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config

# === ENVIRONMENT VARIABLEN ===
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# === TELEGRAM BEFEHLE ===
@app.route("/")
def index():
    return "✅ Monica Option Bot läuft"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hallo! Ich bin dein Monica Option KI-Bot 🤖")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 KI-Status: Läuft aktuell und empfängt Signale.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))

# === TELEGRAM WEBHOOK ===
@app.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK", 200

# === HAUPTSTART ===
async def run():
    port = int(os.environ.get("PORT", 8000))
    webhook_url = f"https://monica-option.onrender.com/webhook"

    print(f"🚀 Setze Webhook auf {webhook_url}")
    await application.bot.set_webhook(webhook_url)

    info = await application.bot.get_webhook_info()
    print("🌐 Webhook-Status:", info)

    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    await serve(app, config)


if __name__ == "__main__":
    asyncio.run(run())
