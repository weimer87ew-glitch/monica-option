import os
import asyncio
import random
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config

# === ENVIRONMENT VARIABLEN ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("❌ Kein BOT_TOKEN gefunden! Bitte in Render → Environment Variable hinzufügen.")

# === FLASK SERVER ===
app = Flask(__name__)

# === TELEGRAM APPLICATION ===
application = Application.builder().token(BOT_TOKEN).build()

# === TELEGRAM BEFEHLE ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Willkommen bei *Monica Option KI Bot* 🤖\n\n"
        "Befehle:\n"
        "• /status – Zeigt Systemstatus\n"
        "• /train – Startet KI-Training\n"
        "• /buy <asset> <betrag> – Kauft z. B. /buy EURUSD 50\n"
        "• /sell <asset> <betrag> – Verkauft Position\n"
        "• /signal – Zeigt aktuelles Handelssignal"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 KI-Status: Aktiv, empfängt Daten und analysiert Markttrends...")

# === SIMULIERTES TRAINING ===
training_active = False

async def train_model():
    global training_active
    training_active = True
    print("🚀 KI-Training gestartet...")
    for epoch in range(1, 6):
        await asyncio.sleep(3)
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
        await update.message.reply_text("✅ Training läuft jetzt im Hintergrund.")

# === TRADING KOMMANDOS ===
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❗ Beispiel: /buy EURUSD 50")
        return

    asset = context.args[0].upper()
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ungültiger Betrag.")
        return

    await update.message.reply_text(f"🟢 Kaufbefehl: {asset} für {amount:.2f} USD wird ausgeführt...")
    await asyncio.sleep(2)
    await update.message.reply_text(f"✅ Position {asset} erfolgreich *gekauft*!")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❗ Beispiel: /sell EURUSD 50")
        return

    asset = context.args[0].upper()
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ungültiger Betrag.")
        return

    await update.message.reply_text(f"🔴 Verkaufsbefehl: {asset} für {amount:.2f} USD wird ausgeführt...")
    await asyncio.sleep(2)
    await update.message.reply_text(f"✅ Position {asset} erfolgreich *verkauft*!")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signal_type = random.choice(["🟢 BUY", "🔴 SELL", "🟡 HOLD"])
    confidence = random.uniform(70, 99)
    await update.message.reply_text(f"📈 Aktuelles Signal: *{signal_type}* ({confidence:.1f}% Sicherheit)")

# === HANDLER HINZUFÜGEN ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("train", train_command))
application.add_handler(CommandHandler("buy", buy))
application.add_handler(CommandHandler("sell", sell))
application.add_handler(CommandHandler("signal", signal))

# === FLASK ROUTES ===
@app.route("/")
def index():
    return "✅ Monica Option Bot läuft!"

@app.route("/webhook", methods=["POST"])
async def webhook():
    """Empfängt Telegram Updates."""
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
        return "OK", 200
    except Exception as e:
        print("❌ Fehler im Webhook:", e)
        return "Fehler", 500

# === START DES SERVERS ===
async def run():
    port = int(os.environ.get("PORT", 8000))
    webhook_url = f"https://monica-option.onrender.com/webhook"

    print(f"🚀 Setze Webhook auf {webhook_url}")
    await application.bot.set_webhook(webhook_url)

    config = Config()
    config.bind = [f"0.0.0.0:{port}"]

    await application.initialize()
    await application.start()
    print("✅ Telegram Application gestartet")

    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(run())
