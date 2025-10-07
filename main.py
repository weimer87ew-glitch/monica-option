import asyncio
import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from hypercorn.asyncio import serve
from hypercorn.config import Config

# === Flask Webserver ===
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Monica Option Hauptbot läuft!"

# === KONFIGURATION ===
TOKEN = "DEIN_TELEGRAM_BOT_TOKEN"  # <-- hier deinen echten Bot-Token einsetzen
BOT_URL = "https://monica-option.onrender.com"  # <-- URL von deinem Hauptbot
WORKER_URL = "https://monica-option-train.onrender.com"  # <-- URL deines KI-Workers (Render-Link)

# === Telegram Bot Application ===
application = Application.builder().token(TOKEN).build()

# === /start ===
async def start(update: Update, context):
    await update.message.reply_text("👋 Monica Option Bot ist bereit! Nutze /train oder /status.")

# === /train: startet das KI-Training im Worker ===
async def train(update: Update, context):
    try:
        response = requests.post(f"{WORKER_URL}/start_training", timeout=10)
        if response.status_code == 200:
            msg = response.json().get("message", "Training gestartet.")
        else:
            msg = f"⚠️ Fehler: {response.text}"
    except Exception as e:
        msg = f"❌ Verbindung zum Worker fehlgeschlagen: {e}"
    await update.message.reply_text(msg)

# === /status: fragt Status vom Worker ab ===
async def status(update: Update, context):
    try:
        response = requests.get(f"{WORKER_URL}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            text = (
                f"📊 **Training-Status:**\n"
                f"- Läuft: {data.get('is_training', False)}\n"
                f"- Episode: {data.get('episode', '—')}\n"
                f"- Letzte Belohnung: {data.get('last_reward', '—')}\n"
                f"- Durchschnitt (10): {data.get('avg_reward_10', '—')}\n"
                f"- Epsilon: {data.get('epsilon', '—')}\n"
                f"- Zeit: {data.get('elapsed_s', '—')}s"
            )
        else:
            text = f"⚠️ Fehler: {response.text}"
    except Exception as e:
        text = f"❌ Verbindung zum Worker fehlgeschlagen: {e}"
    await update.message.reply_text(text)

# === Telegram Handler ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))
application.add_handler(CommandHandler("status", status))

# === Globaler Event Loop ===
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# === Webhook Endpoint ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    loop.create_task(application.process_update(update))
    return "OK", 200

# === BOT START ===
async def run_bot():
    await application.initialize()
    await application.bot.set_webhook(url=f"{BOT_URL}/{TOKEN}")
    print("✅ Webhook aktiv!")
    print("🤖 Monica Option Bot läuft...")
    await asyncio.Event().wait()

async def run_web():
    config = Config()
    config.bind = ["0.0.0.0:10000"]
    await serve(app, config)

async def main():
    await asyncio.gather(run_bot(), run_web())

if __name__ == "__main__":
    loop.run_until_complete(main())
