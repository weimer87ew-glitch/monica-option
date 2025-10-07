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

# === Telegram Setup ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("❌ Kein BOT_TOKEN gefunden! Bitte in Render → Environment Variable hinzufügen.")
if not CHAT_ID:
    raise ValueError("❌ Kein TELEGRAM_CHAT_ID gefunden! Bitte in Render → Environment Variable hinzufügen.")

# === Trainingsstatus global speichern ===
training_status = {"running": False, "accuracy": None, "message": ""}

# === Telegram Bot Instanz ===
application = Application.builder().token(BOT_TOKEN).build()

# === KI-Training Funktion ===
async def train_model():
    global training_status
    training_status["running"] = True
    training_status["message"] = "📈 Training gestartet..."

    try:
        # 1️⃣ Marktdaten laden (EUR/USD)
        df = yf.download("EURUSD=X", period="1mo", interval="1h")
        df.dropna(inplace=True)

        if len(df) < 10:
            training_status["message"] = "❌ Zu wenige Daten für Training."
            training_status["running"] = False
            return

        # 2️⃣ Features & Zielwerte vorbereiten
        df["Target"] = df["Close"].shift(-1)
        X = df[["Open", "High", "Low", "Close"]].iloc[:-1]
        y = df["Target"].iloc[:-1]

        # 3️⃣ Modell trainieren
        model = LinearRegression()
        model.fit(X, y)

        # 4️⃣ Genauigkeit berechnen
        accuracy = model.score(X, y)
        training_status["accuracy"] = round(accuracy * 100, 2)
        training_status["message"] = f"✅ Training abgeschlossen! Genauigkeit: {training_status['accuracy']}%"

        # 5️⃣ Telegram-Benachrichtigung nach Abschluss
        await application.bot.send_message(
            chat_id=CHAT_ID,
            text=f"🎯 KI-Training abgeschlossen!\nGenauigkeit: {training_status['accuracy']}%"
        )

    except Exception as e:
        training_status["message"] = f"❌ Fehler beim Training: {e}"

    training_status["running"] = False


# === Telegram Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hallo! Ich bin Monica Option – dein KI-Trading-Bot.\n\n"
        "Verfügbare Befehle:\n"
        "📊 /train – starte KI-Training\n"
        "📡 /status – zeige aktuellen Status\n"
        "📈 /predict – erhalte eine Marktprognose"
    )

async def train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if training_status["running"]:
        await update.message.reply_text("⚙️ Training läuft bereits...")
    else:
        await update.message.reply_text("📊 Starte echtes KI-Training... Bitte warten ⏳")
        asyncio.create_task(train_model())

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"📡 Status: {'läuft' if training_status['running'] else 'bereit'}\n"
    if training_status["accuracy"]:
        msg += f"🎯 Genauigkeit: {training_status['accuracy']}%\n"
    msg += f"ℹ️ Info: {training_status['message']}"
    await update.message.reply_text(msg)

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = yf.download("EURUSD=X", period="1d", interval="1h")
    if df.empty:
        await update.message.reply_text("❌ Keine Daten verfügbar.")
        return
    last = df.iloc[-1]
    change = last["Close"] - last["Open"]
    signal = "📈 BUY" if change > 0 else "📉 SELL"
    await update.message.reply_text(f"Letzter Trend: {signal}\nVeränderung: {round(change, 5)}")


# === Flask Routes ===
@app.route('/')
def index():
    return "✅ Monica Option Bot läuft."

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"


# === Telegram Bot starten ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("predict", predict))


# === Hypercorn Server Start ===
if __name__ == "__main__":
    config = Config()
    config.bind = ["0.0.0.0:10000"]
    asyncio.run(serve(app, config))
