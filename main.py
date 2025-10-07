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

# === TELEGRAM APPLICATION ===
application = Application.builder().token(TOKEN).build()

# === TELEGRAM BEFEHLE ===
@app.route("/")
def index():
    return "✅ Monica Option Bot läuft!"

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
async def main():
    port = int(os.environ.get("PORT", 8000))
    webhook_url = f"https://monica-option-train.onrender.com/webhook"

    # 1️⃣ Telegram Bot vorbereiten
    print(f"🚀 Setze Webhook auf {webhook_url}")
    await application.initialize()
    await application.bot.set_webhook(webhook_url)
    await application.start()
    print("✅ Telegram-Bot gestartet")

    # 2️⃣ Hypercorn-Server starten
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    await serve(app, config)

    # 3️⃣ Stop-Handler für sauberes Beenden
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Server gestoppt")
