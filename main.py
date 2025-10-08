import os
import asyncio
import threading
import time
import json
import requests
import pandas as pd
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from sklearn.linear_model import LinearRegression
import joblib
from hypercorn.asyncio import serve
from hypercorn.config import Config
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === CONFIG / ENV ===
app = Quart(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or "https://monica-option.onrender.com"
TWELVE_API_KEY = os.getenv("TWELVEDATA_KEY")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN fehlt in Environment Variables")
if not TWELVE_API_KEY:
    raise RuntimeError("TWELVEDATA_KEY fehlt — bitte TwelveData API-Key setzen")

application = Application.builder().token(BOT_TOKEN).build()

# === GLOBALS ===
training_status = {"running": False, "accuracy": None, "message": ""}
MODEL_PATH = "eurusd_model.pkl"


# === TwelveData Download ===
def get_twelvedata(symbol="EUR/USD", interval="5min", outputsize=500):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVE_API_KEY,
        "format": "JSON",
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if "values" not in data:
        raise ValueError(f"TwelveData Fehler: {data}")
    df = pd.DataFrame(data["values"])
    df = df.astype({
        "open": float, "high": float, "low": float, "close": float
    })
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.sort_values("datetime", inplace=True)
    return df


# === MODEL TRAINING ===
async def train_model():
    global training_status
    training_status["running"] = True
    training_status["message"] = "📈 Training gestartet..."
    print(training_status["message"])

    try:
        df = get_twelvedata()
        if len(df) < 20:
            training_status["message"] = "❌ Zu wenige Daten von TwelveData."
            return

        df["target"] = df["close"].shift(-1)
        df.dropna(inplace=True)
        X = df[["open", "high", "low", "close"]]
        y = df["target"]

        model = LinearRegression()
        model.fit(X, y)

        acc = model.score(X, y)
        training_status["accuracy"] = round(acc * 100, 2)
        training_status["message"] = f"✅ Training fertig ({training_status['accuracy']}%)"

        # Modell speichern
        joblib.dump(model, MODEL_PATH)
        print(training_status["message"])

    except Exception as e:
        training_status["message"] = f"❌ Fehler beim Training: {e}"
        print(training_status["message"])
    finally:
        training_status["running"] = False


# === PREDICT ===
async def predict_price():
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError("Kein trainiertes Modell gefunden.")
    model = joblib.load(MODEL_PATH)
    df = get_twelvedata(symbol="EUR/USD", interval="5min", outputsize=5)
    last = df.iloc[-1]
    X_pred = [[last["open"], last["high"], last["low"], last["close"]]]
    y_pred = model.predict(X_pred)[0]
    delta = y_pred - last["close"]
    signal = "📈 BUY" if delta > 0 else "📉 SELL"
    return signal, delta


# === TELEGRAM COMMANDS ===
async def start(update, context):
    await update.message.reply_text("👋 Monica Option Bot aktiv. Befehle: /train /status /predict")

async def train(update, context):
    if training_status["running"]:
        await update.message.reply_text("⚙️ Training läuft bereits...")
    else:
        await update.message.reply_text("📊 Starte Training...")
        asyncio.create_task(train_model())

async def status(update, context):
    msg = f"📡 Status: {'läuft' if training_status['running'] else 'bereit'}"
    if training_status["accuracy"]:
        msg += f"\n🎯 Genauigkeit: {training_status['accuracy']}%"
    await update.message.reply_text(msg)

async def predict(update, context):
    try:
        signal, delta = await predict_price()
        await update.message.reply_text(f"{signal} — Δ {round(delta,5)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {e}")


# register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("predict", predict))


# === AUTO TRAINING (alle 6h) ===
async def periodic_training():
    while True:
        await train_model()
        print("⏳ Warte 6 Stunden bis zum nächsten Training...")
        await asyncio.sleep(6 * 60 * 60)


# === WATCHDOG (Auto-Restart bei Codeänderung) ===
class RestartHandler(FileSystemEventHandler):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self._last = 0.0

    def on_modified(self, event):
        if not event.src_path.endswith(".py"):
            return
        now = time.time()
        if now - self._last < 1.0:
            return
        self._last = now
        print(f"♻️ Dateiänderung erkannt: {event.src_path} -> Neustart")
        if CHAT_ID:
            coro = application.bot.send_message(chat_id=CHAT_ID, text="🔄 Bot wird neu gestartet (Code-Update)...")
            asyncio.run_coroutine_threadsafe(coro, self.loop)
        time.sleep(0.5)
        os._exit(0)


def start_watchdog(loop):
    handler = RestartHandler(loop)
    observer = Observer()
    observer.schedule(handler, ".", recursive=True)
    observer.start()
    print("🔍 Watchdog läuft (überwacht .py Dateien)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# === QUART ROUTES ===
@app.route("/")
async def index():
    return "✅ Monica Option Bot läuft (TwelveData, 5min, 6h Retraining)."

@app.route("/webhook", methods=["POST"])
async def webhook():
    data = await request.get_json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK"


# === MAIN ===
async def main():
    print("🚀 Initialisiere Bot...")
    await application.initialize()

    webhook_url = f"{RENDER_URL}/webhook"
    await application.bot.set_webhook(webhook_url)
    print(f"✅ Webhook gesetzt: {webhook_url}")

    if CHAT_ID:
        try:
            await application.bot.send_message(chat_id=CHAT_ID, text="✅ Bot gestartet (TwelveData + AutoTrain).")
        except Exception as e:
            print("Info: Startup-Message fehlgeschlagen:", e)

    loop = asyncio.get_running_loop()
    threading.Thread(target=start_watchdog, args=(loop,), daemon=True).start()

    # Auto-Training im Hintergrund
    asyncio.create_task(periodic_training())

    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    await serve(app, config)


if __name__ == "__main__":
    asyncio.run(main())
