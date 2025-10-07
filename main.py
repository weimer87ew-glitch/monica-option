import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config

import yfinance as yf
import pandas as pd
from sklearn.linear_model import LinearRegression

# === Flask App ===
app = Flask(__name__)

BOT_TOKEN = "DEIN_TELEGRAM_BOT_TOKEN"

# === Telegram Bot initialisieren ===
application = Application.builder().token(BOT_TOKEN).build()

# === Beispiel-Funktion: Startkommando ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Monica Option Bot läuft!")

application.add_handler(CommandHandler("start", start))

# === Flask Route: Statusanzeige ===
@app.route('/')
def index():
    return "✅ Monica Option Bot läuft auf Render.com!"

# === Webhook Endpoint ===
@app.route('/webhook', methods=['POST'])
def webhook():
    """Verarbeitet eingehende Telegram-Updates (async-sicher)."""
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)

        # Prüfen, ob bereits ein Event-Loop existiert (Python 3.13 braucht das)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Wenn ein Loop aktiv ist → Task dort starten
            loop.create_task(application.process_update(update))
        else:
            # Wenn kein Loop aktiv ist → neuen erstellen
            asyncio.run(application.process_update(update))

    except Exception as e:
        print(f"❌ Fehler im Webhook: {e}")
    return "OK", 200

# === Trading Beispiel (Dummy) ===
def simple_prediction(symbol: str):
    data = yf.download(symbol, period="7d", interval="1h")
    if len(data) < 2:
        return "Nicht genug Daten."

    data["Return"] = data["Close"].pct_change().fillna(0)
    X = (data.index - data.index[0]).total_seconds().values.reshape(-1, 1)
    y = data["Return"].values

    model = LinearRegression()
    model.fit(X, y)
    trend = model.predict([[X[-1][0] + 3600]])[0]
    if trend > 0:
        return f"📈 Signal: Kaufempfehlung ({trend:.4f})"
    else:
        return f"📉 Signal: Verkaufsempfehlung ({trend:.4f})"

# === Test-Route ===
@app.route('/predict/<symbol>')
def predict(symbol):
    try:
        return simple_prediction(symbol.upper())
    except Exception as e:
        return f"❌ Fehler: {e}"

# === Hypercorn Server starten ===
if __name__ == "__main__":
    config = Config()
    config.bind = ["0.0.0.0:10000"]
    config.use_uvloop = False  # 🚫 uvloop deaktivieren für Python 3.13
    config.use_reloader = False

    # Anwendung asynchron starten
    asyncio.run(serve(app, config))
