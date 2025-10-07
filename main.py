import os
import asyncio
import random
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config

# === ENVIRONMENT VARIABLEN ===
webhook_url = f"https://monica-option.onrender.com/webhook"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging

# ========================================
# LOGGING AKTIVIEREN (zeigt Fehler im Render-Log)
# ========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================================
# FLASK APP
# ========================================
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Monica Option Bot läuft auf Render!"

# ========================================
# TELEGRAM TOKEN & CHAT-ID AUS ENVIRONMENT
# ========================================
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN:
    raise ValueError("❌ Kein BOT_TOKEN gefunden! Bitte in Render → Environment Variable hinzufügen.")

# ========================================
# TELEGRAM BOT HANDLER
# ========================================

async def start(update: Update, context):
    await update.message.reply_text("👋 Hallo, ich bin Monica Option – dein Trading KI Bot!")

async def echo(update: Update, context):
    text = update.message.text
    logger.info(f"Nachricht erhalten: {text}")
    await update.message.reply_text(f"💬 Du hast gesagt: {text}")

# ========================================
# TELEGRAM APPLICATION
# ========================================
application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# ========================================
# FLASK ENDPOINT FÜR TELEGRAM WEBHOOK
# ========================================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

# ========================================
# STARTUP FUNKTION FÜR WEBHOOK (Render)
# ========================================
async def set_webhook():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    if webhook_url:
        await application.bot.set_webhook(webhook_url)
        logger.info(f"🌐 Webhook gesetzt: {webhook_url}")
    else:
        logger.warning("⚠️ Konnte RENDER_EXTERNAL_HOSTNAME nicht finden – Webhook manuell setzen!")

# ========================================
# STARTEN
# ========================================
if __name__ == '__main__':
    import threading

    # Telegram-Bot in separatem Thread starten
    def run_bot():
        asyncio.run(set_webhook())
        logger.info("🤖 Telegram-Bot läuft jetzt!")

    threading.Thread(target=run_bot).start()

    # Flask starten (Render erwartet Port)
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Starte Flask auf Port {port}")
    app.run(host='0.0.0.0', port=port)

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# === TELEGRAM BEFEHLE ===
@app.route("/")
def index():
    return "✅ Monica Option Bot läuft (mit Training integriert)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hallo! Ich bin dein Monica Option KI-Bot 🤖")
    await update.message.reply_text("Nutze /status für KI-Status oder /train um Training zu starten.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 KI-Status: Läuft aktuell und empfängt Signale.")

# === TRAININGSFUNKTION ===
training_active = False

async def train_model():
    global training_active
    training_active = True
    print("🚀 Training gestartet...")

    # Beispielhafte Trainingssimulation
    for epoch in range(1, 6):
        await asyncio.sleep(3)  # simuliert Training pro Epoche
        accuracy = random.uniform(70, 99)
        print(f"📈 Epoche {epoch}/5 abgeschlossen – Genauigkeit: {accuracy:.2f}%")

    print("✅ Training abgeschlossen!")
    training_active = False

async def train_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if training_active:
        await update.message.reply_text("⚙️ Training läuft bereits...")
    else:
        await update.message.reply_text("🚀 Starte neues KI-Training...")
        asyncio.create_task(train_model())
        await update.message.reply_text("✅ Training läuft jetzt im Hintergrund. Ich informiere dich, wenn es fertig ist.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("train", train_command))

# === TELEGRAM WEBHOOK ===
@app.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK", 200

# === START DES SERVERS ===
async def run():
    port = int(os.environ.get("PORT", 8000))
    webhook_url = f"https://monica-option.onrender.com/{TOKEN}"

    print(f"🚀 Setze Webhook auf {webhook_url}")
    await application.bot.set_webhook(webhook_url)

    info = await application.bot.get_webhook_info()
    print("🌐 Webhook-Status:", info)

    config = Config()
    config.bind = [f"0.0.0.0:{port}"]

    # Starte gleichzeitig Flask (für Telegram) und KI-Training
    await asyncio.gather(application.initialize(), serve(app, config))

if __name__ == "__main__":
    asyncio.run(run())
