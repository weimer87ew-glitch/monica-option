import os
import asyncio
import yfinance as yf
import pandas as pd
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from sklearn.linear_model import LinearRegression
from hypercorn.asyncio import serve
from hypercorn.config import Config

# === Flask App ===
app = Flask(__name__)

# === Environment Variablen ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or "https://monica-option.onrender.com"

if not BOT_TOKEN:
    raise ValueError("❌ Kein BOT_TOKEN gefunden! Bitte in Render → Environment Variable hinzufügen.")
if not CHAT_ID:
    raise ValueError("❌ Kein TELEGRAM_CHAT_ID gefunden! Bitte in Render → Environment Variable hinzufügen.")

# === Telegram Bot Application ===
application = Application.builder().token(BOT_TOKEN).build()
initialized = False

training_status = {"running": False, "accuracy": None, "message": ""}


# === KI-Training ===
async def train_model():
    global training_status
    training_status["running"] = True
    training_status["message"] = "📈 Training gestartet..."
    print(training_status["message"])

    df = yf.download("EURUSD=X", period="1mo", interval="1h")
    df.dropna(inplace=True)

    if len(df) < 10:
        training_status["message"] = "❌ Zu wenige Daten für Training."
        training_status["running"] = False
        return

    df["Target"] = df["Close"].shift(-1)
    X = df[["Open", "High", "Low", "Close"]].iloc[:-1]
    y = df["Target"].iloc[:-1]

    model = LinearRegression()
    model.fit(X, y)

    acc = model.score(X, y)
    training_status["accuracy"] = round(acc * 100, 2)
    training_status["message"] = f"✅ Training abgeschlossen! Genauigkeit: {training_status['accuracy']}%"
    training_status["running"] = False
    print(training_status["message"])


# === Telegram Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hallo! Ich bin Monica Option – dein KI-Trading-Bot.\n"
        "Verfügbare Befehle:\n"
        "/train – Modell trainieren\n"
        "/status – Trainingsstatus\n"
        "/predict – Marktprognose anzeigen"
    )


async def train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if training_status["running"]:
        await update.message.reply_text("⚙️ Training läuft bereits...")
    else:
        await update.message.reply_text("📊 Starte KI-Training... Bitte warten ⏳")
        asyncio.create_task(train_model())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"📡 Status: {'läuft' if training_status['running'] else 'bereit'}\n"
    if training_status["accuracy"]:
        msg += f"🎯 Genauigkeit: {training_status['accuracy']}%"
    await update.message.reply_text(msg)


async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = yf.download("EURUSD=X", period="1d", interval="1h")
    if df.empty:
        await update.message.reply_text("❌ Keine Daten verfügbar.")
        return
    last = df.iloc[-1]
    signal = "📈 BUY" if last["Close"] > last["Open"] else "📉 SELL"
    change = round(last["Close"] - last["Open"], 5)
    await update.message.reply_text(f"Letzter Trend: {signal}\nVeränderung: {change}")


# === Handler ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("predict", predict))


# === Flask Routes ===
@app.route('/')
def index():
    return "✅ Monica Option Bot läuft."


@app.route('/webhook', methods=['POST'])
def webhook():
    global initialized
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    if not initialized:
        print("⚠️ Webhook-Aufruf vor Initialisierung — übersprungen.")
        return "Not ready", 503

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(application.process_update(update))
        return "OK", 200
    except Exception as e:
        print(f"❌ Fehler im Webhook: {e}")
        return "Error", 500


# === Start Server ===
if __name__ == "__main__":
    async def main():
        global initialized
        print("🚀 Initialisiere Bot...")
        await application.initialize()

        webhook_url = f"{RENDER_URL}/webhook"
        await application.bot.delete_webhook()
        await application.bot.set_webhook(webhook_url)
        print(f"🌍 Webhook gesetzt auf: {webhook_url}")

        initialized = True
        print("✅ Bot ist bereit und Webhook aktiv!")

        config = Config()
        config.bind = ["0.0.0.0:10000"]
        config.use_reloader = False  # <— verhindert Render-Reinitialisierung
        await serve(app, config)

    asyncio.run(main())
