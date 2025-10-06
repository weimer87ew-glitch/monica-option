import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from hypercorn.asyncio import serve
from hypercorn.config import Config
import os

# === Flask Setup ===
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Monica Option Bot läuft!"

# === Telegram Setup ===
TOKEN = "8228792401:AAErviwIbHLCLQL2ybraKO-d08pbS_GFMhk"  # hier deinen Token eintragen
BOT_URL = "https://monica-option.onrender.com"

application = Application.builder().token(TOKEN).build()

# einfache Start-Nachricht
async def start(update: Update, context):
    await update.message.reply_text("👋 Hallo! Monica Option Bot ist aktiv!")

application.add_handler(CommandHandler("start", start))

# === Webhook Endpoint ===
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    """Empfängt Telegram-Updates."""
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK", 200

# === Async Tasks ===
async def run_bot():
    await application.initialize()
    await application.bot.set_webhook(url=f"{BOT_URL}/{TOKEN}")
    print("✅ Webhook erfolgreich gesetzt!")
    print("🤖 Monica Option Bot ist bereit.")
    await asyncio.Event().wait()

async def run_web():
    config = Config()
    config.bind = ["0.0.0.0:10000"]
    await serve(app, config)

async def main():
    await asyncio.gather(run_bot(), run_web())

if __name__ == "__main__":
    asyncio.run(main())


