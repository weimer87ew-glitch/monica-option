import os
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- Flask Setup ---
app = Flask(__name__)

@app.route('/')
def home():
    return {"alive": True, "message": "Monica Option Bot is running!"}

# --- Telegram Bot Setup ---
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hallo! Ich bin Monica Option — dein Trading-Assistent.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📘 Befehle:\n/start – Begrüßung\n/help – Hilfe\n/train – KI-Training starten")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text(f"Du sagtest: {user_message}")

async def run_telegram_bot():
    if not TOKEN:
        print("❌ Kein TELEGRAM_TOKEN gefunden!")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("🤖 Monica Option Bot läuft...")
    await app.run_polling()

async def main():
    # Starte Telegram-Bot im Hintergrund
    asyncio.create_task(run_telegram_bot())

    # Starte Flask synchron im selben Event Loop
    port = int(os.environ.get("PORT", 10000))
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = [f"0.0.0.0:{port}"]

    print(f"🌐 Webserver läuft auf Port {port}")
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
