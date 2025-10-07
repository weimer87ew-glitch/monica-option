import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config

# ==========================================================
#   CONFIGURATION
# ==========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "DEIN_TELEGRAM_BOT_TOKEN_HIER")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://monica-option.onrender.com/webhook")

app = Flask(__name__)

# ==========================================================
#   TELEGRAM BOT SETUP
# ==========================================================
application = Application.builder().token(BOT_TOKEN).build()


# Beispiel-Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hallo! Monica Option Bot ist aktiv!")


# Beispiel-Funktion für Strategieprüfung
async def analyse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Strategieanalyse läuft... (Demo)")


application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("analyse", analyse))


# ==========================================================
#   WEBHOOK HANDLER (Render-kompatibel)
# ==========================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Wenn kein aktiver Event Loop existiert (z. B. auf Render)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(application.process_update(update))
    return "OK", 200


# ==========================================================
#   ROOT ROUTE
# ==========================================================
@app.route("/")
def index():
    return "✅ Monica Option Bot läuft erfolgreich auf Render!"


# ==========================================================
#   STARTUP TASK
# ==========================================================
async def startup():
    # Setzt Webhook beim Start
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print(f"🚀 Webhook gesetzt auf: {WEBHOOK_URL}")


# ==========================================================
#   SERVER START
# ==========================================================
if __name__ == "__main__":
    config = Config()
    config.bind = ["0.0.0.0:10000"]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Starte sowohl Bot-Webhook als auch Flask über Hypercorn
    loop.run_until_complete(startup())
    loop.run_until_complete(serve(app, config))
