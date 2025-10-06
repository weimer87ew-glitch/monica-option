import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import os

# -----------------------------
# 🧩 Konfiguration
# -----------------------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # sicherer: über Render-Umgebung setzen
WEBHOOK_URL = "https://monica-option.onrender.com/webhook"  # deine Render-URL

app = Flask(__name__)

# -----------------------------
# 🤖 Telegram-Setup
# -----------------------------
application = Application.builder().token(TOKEN).build()


# Beispielbefehl /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hallo, ich bin dein Monica Option Bot! 🚀")


# Befehle registrieren
application.add_handler(CommandHandler("start", start))


# -----------------------------
# 🌍 Flask-Routen
# -----------------------------
@app.route("/")
def index():
    return "✅ Monica Option Bot läuft über Webhook!"


# Telegram sendet Updates an diesen Endpoint:
@app.route("/webhook", methods=["POST"])
def webhook():
    """Empfängt Updates von Telegram"""
    data = request.get_json(force=True)
    asyncio.create_task(application.process_update(Update.de_json(data, application.bot)))
    return "ok", 200


# -----------------------------
# 🚀 Start des Bots
# -----------------------------
async def main():
    # Setzt neuen Webhook (löscht alten automatisch)
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print(f"🌐 Webhook gesetzt auf: {WEBHOOK_URL}")

    # Flask Server starten
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:10000"]
    await serve(app, config)


if __name__ == "__main__":
    asyncio.run(main())


