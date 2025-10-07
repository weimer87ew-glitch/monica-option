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

# === Telegram Bot Anwendung ===
application = Application.builder().token(BOT_TOKEN).build()

# === Statusspeicher ===
training_status = {"running": False, "accuracy": None, "message": ""}

# === KI-Trainingsfunktion ===
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

# === Telegram Befehle ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hallo! Ich bin Monica Option – dein KI-Trading-Bot.\n"
        "Verfügbare Befehle:\n"
        "/train – Starte KI-Training\n"
        "/status – Zeige Trainingsstatus\n"
        "/predict – Marktprognose anzeigen"
    )

async def train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if training_status["running"]:
        await update.message.reply_text("⚙️ Training läuft bereits...")
    else:
        await update.message.reply_text("📊 Starte KI-Training... Bitte warten ⏳")
        asyncio.create_task(train_model())

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"📡 Status: {'läuft' if training_status['running'] else 'bereit'}"
    if training_status["accuracy"]:
        msg += f"\n🎯 Genauigkeit: {training_status['accuracy']}%"
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

# === Handler ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("predict", predict))

# === Flask Routes ===
@app.route("/")
def home():
    return "✅ Monica Option Bot läuft."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(application.process_update(update))
    else:
        loop.run_until_complete(application.process_update(update))

    return "ok", 200

# === Start (Render-kompatibel) ===
if __name__ == "__main__":
    async def main():
        print("🚀 Starte Monica Option...")
        await application.initialize()

        webhook_url = f"{RENDER_URL}/webhook"
        print(f"🌍 Setze Webhook auf: {webhook_url}")
        await application.bot.set_webhook(webhook_url)
        print("✅ Webhook gesetzt & Bot initialisiert!")

        config = Config()
        config.bind = ["0.0.0.0:10000"]
        await serve(app, config)

    asyncio.run(main())
