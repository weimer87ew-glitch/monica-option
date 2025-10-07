import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config
import threading

# === ENVIRONMENT VARIABLEN ===
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# === TELEGRAM BEFEHLE ===
@app.route("/")
def index():
    return "✅ Monica Option Bot läuft!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hallo 👋 Ich bin dein Monica Option KI-Bot 🤖")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 KI-Status: Läuft und empfängt Trading-Signale.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))

# === ASYNC HANDLER ===
def run_async(coro):
    """Sicheres Starten einer Async-Funktion in eigenem Event Loop."""
    def runner():
        asyncio.run(coro)
    threading.Thread(target=runner).start()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    run_async(application.process_update(update))
    return "OK", 200

# === SERVER START ===
async def main():
    port = int(os.environ.get("PORT", 8000))
    webhook_url = "https://monica-option.onrender.com/webhook"

    print(f"🚀 Setze Telegram Webhook: {webhook_url}")
    await application.initialize()
    await application.bot.set_webhook(webhook_url)
    await application.start()
    print("✅ Telegram-Bot gestartet!")

    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    await serve(app, config)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Server gestoppt")
