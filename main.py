import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Flask Webserver für Render "Alive" Ping
app = Flask(__name__)

@app.route('/')
def home():
    return {"alive": True, "message": "Monica Option Bot is running!"}

# Telegram Bot Funktionen
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hallo! Ich bin Monica Option — dein Trading-Assistent.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📘 Befehle:\n/start – Begrüßung\n/help – Hilfe\n/train – KI-Training starten")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text(f"Du sagtest: {user_message}")

def run_telegram_bot():
    if not TOKEN:
        print("❌ Kein TELEGRAM_TOKEN gefunden!")
        return

    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("🤖 Monica Option Bot läuft...")
    bot_app.run_polling()

if __name__ == "__main__":
    # Starte Telegram-Bot in separatem Thread
    threading.Thread(target=run_telegram_bot).start()
    # Starte Webserver für Render
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
