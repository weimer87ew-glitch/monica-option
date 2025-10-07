import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from hypercorn.asyncio import serve
from hypercorn.config import Config
import requests
import os

# === KI-Worker Verbindung ===
WORKER_URL = os.getenv("WORKER_URL", "https://monica-option-train.onrender.com")

# Flask App
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Monica Option Bot läuft!"

# === BOT TOKEN UND URL ===
TOKEN = "8228792401:AAErviwIbHLCLQL2ybraKO-d08pbS_GFMhk"  # ⬅️ Deinen echten Token einsetzen!
BOT_URL = "https://monica-option.onrender.com"

# === Telegram Application ===
application = Application.builder().token(TOKEN).build()

# === Einfacher /start Command ===
async def start(update: Update, context):
    await update.message.reply_text("👋 Hallo! Monica Option Bot ist aktiv!")

# ✅ HIER neuen Code EINFÜGEN:
# === KI-Kommandos ===
async def train(update: Update, context):
    await update.message.reply_text("🚀 Sende Trainingsauftrag an KI-Worker...")
    try:
        r = requests.post(f"{WORKER_URL}/start_training")
        if r.status_code == 200:
            await update.message.reply_text("✅ Training gestartet! Ich melde mich, sobald es fertig ist.")
        else:
            await update.message.reply_text("⚠️ Fehler beim Starten des Trainings.")
    except Exception as e:
        await update.message.reply_text(f"❌ Verbindung zum Worker fehlgeschlagen: {e}")

async def status(update: Update, context):
    try:
        r = requests.get(f"{WORKER_URL}/status")
        if r.status_code == 200:
            await update.message.reply_text(f"📊 KI-Status:\n{r.text}")
        else:
            await update.message.reply_text("⚠️ Fehler beim Abfragen des Status.")
    except Exception as e:
        await update.message.reply_text(f"❌ Keine Verbindung zum Worker: {e}")

# === Handler registrieren ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))     # 👈 neu
application.add_handler(CommandHandler("status", status))   # 👈 neu

# === GLOBALER LOOP ===
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# === Webhook Endpoint ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    loop.create_task(application.process_update(update))  # <-- globaler Loop, kein Fehler!
    return "OK", 200

# === BOT STARTEN ===
async def run_bot():
    await application.initialize()
    await application.bot.set_webhook(url=f"{BOT_URL}/{TOKEN}")
    print("✅ Webhook erfolgreich gesetzt!")
    print("🤖 Monica Option Bot ist bereit.")
    await asyncio.Event().wait()  # hält ihn am Laufen

async def run_web():
    config = Config()
    config.bind = ["0.0.0.0:10000"]
    await serve(app, config)

async def main():
    await asyncio.gather(run_bot(), run_web())

if __name__ == "__main__":
    loop.run_until_complete(main())
