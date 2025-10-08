import os
import asyncio
import yfinance as yf
import pandas as pd
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from sklearn.linear_model import LinearRegression
from hypercorn.asyncio import serve
from hypercorn.config import Config


# === Quart App ===
app = Quart(__name__)

# === Environment Variablen ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or "https://monica-option.onrender.com"

if not BOT_TOKEN:
    raise ValueError("❌ Kein BOT_TOKEN gefunden! Bitte in Render → Environment Variables hinzufügen.")
if not CHAT_ID:
    raise ValueError("❌ Kein TELEGRAM_CHAT_ID gefunden! Bitte in Render → Environment Variables hinzufügen.")

# === Telegram Application ===
application = Application.builder().token(BOT_TOKEN).build()

# === Status ===
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

    accuracy = model.score(X, y)
    training_status["accuracy"] = round(accuracy * 100, 2)
    training_status["message"] = f"✅ Training abgeschlossen! Genauigkeit: {training_status['accuracy']}%"
    training_status["running"] = False
    print(training_status["message"])


# === Telegram Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hallo! Ich bin *Monica Option* – dein KI-Trading-Bot.\n"
        "Verfügbare Befehle:\n"
        "/train → Modell trainieren\n"
        "/status → Status anzeigen\n"
        "/predict → Prognose anzeigen",
        parse_mode="Markdown"
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
        await update.message.reply_text("❌ Keine Marktdaten verfügbar.")
        return
    last = df.iloc[-1]
    signal = "📈 BUY" if last["Close"] > last["Open"] else "📉 SELL"
    await update.message.reply_text(f"Letzter Trend: {signal}\nOpen: {last['Open']:.5f}, Close: {last['Close']:.5f}")


# === Command Handler registrieren ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("predict", predict))


# === Quart Routes ===
@app.route("/")
async def index():
    return "✅ Monica Option Bot läuft (Quart-Version)."


@app.route("/webhook", methods=["POST"])
async def webhook():
    data = await request.get_json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK", 200


# === Serverstart + Webhook-Setup ===
if __name__ == "__main__":
    async def main():
        print("🚀 Initialisiere Bot...")
        await application.initialize()

        webhook_url = f"{RENDER_URL}/webhook"
        await application.bot.set_webhook(webhook_url)
        print(f"✅ Webhook gesetzt auf: {webhook_url}")

        config = Config()
        config.bind = ["0.0.0.0:10000"]
        await serve(app, config)

    asyncio.run(main())
