import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")  # Dein Bot-Token von BotFather
app = Flask(__name__)

# Telegram Bot Setup
application = Application.builder().token(TOKEN).build()

@app.route("/")
def index():
    return "✅ Monica Option Bot läuft"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hallo! Ich bin dein Monica Option KI-Bot 🤖")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 KI-Status: Läuft aktuell.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))

# Flask async bridge to telegram
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK"

async def run():
    port = int(os.environ.get("PORT", 8000))
    await application.bot.set_webhook(f"https://monica-option.onrender.com/{TOKEN}")
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(run())
