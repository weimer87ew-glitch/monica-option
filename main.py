import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request

TOKEN = "8228792401:AAErviwIbHLCLQL2ybraKO-d08pbS_GFMhk"  # <-- Hier dein echter Token rein
WEBHOOK_URL = "https://monica-option.onrender.com"  # <-- Hier deine Render-URL rein

# Flask App für Render Healthcheck + Webhook
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Monica Option Bot läuft über Webhook!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(bot.process_update(update))
    return "OK", 200

# Telegram Bot Befehle
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hallo! Monica Option Bot ist aktiv!")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Dies ist dein Trading-Assistent auf Telegram!")

# Setup Telegram Bot
app_telegram = Application.builder().token(TOKEN).build()
bot = app_telegram.bot

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("info", info))

async def main():
    # Webhook setzen
    await bot.delete_webhook()
    await bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    print("🌐 Webhook erfolgreich gesetzt.")
    print("🤖 Monica Option Bot ist bereit.")

if __name__ == "__main__":
    asyncio.run(main())
    app.run(host="0.0.0.0", port=10000)

