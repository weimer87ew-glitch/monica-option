import os
import asyncio
import threading
import time
import yfinance as yf
import pandas as pd
import requests
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from sklearn.linear_model import LinearRegression
from hypercorn.asyncio import serve
from hypercorn.config import Config
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === App / Env ===
app = Quart(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or "https://monica-option.onrender.com"
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN fehlt in Environment Variables")
if not CHAT_ID:
    print("⚠️ WARN: TELEGRAM_CHAT_ID nicht gesetzt — Benachrichtigungen deaktiviert.")

# === Telegram Application ===
application = Application.builder().token(BOT_TOKEN).build()

# === Trainingsstatus ===
training_status = {"running": False, "accuracy": None, "message": ""}


# === DATENABRUF (robust, mit Fallback) ===
def get_forex_data(symbol="EURUSD=X", period="1mo", interval="1h"):
    """Versuche Yahoo Finance, dann Fallback auf TwelveData."""
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if not df.empty:
            return df
        raise ValueError("Leere Yahoo-Daten")
    except Exception as e:
        print(f"⚠️ Yahoo Finance Fehler: {e}")
        # Fallback auf TwelveData
        if not TWELVEDATA_KEY:
            print("❌ Kein TWELVEDATA_KEY im Environment gesetzt — kein Fallback möglich.")
            return pd.DataFrame()

        url = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval={interval}&outputsize=500&apikey={TWELVEDATA_KEY}"
        try:
            r = requests.get(url)
            data = r.json()
            if "values" in data:
                df = pd.DataFrame(data["values"])
                df["datetime"] = pd.to_datetime(df["datetime"])
                df.set_index("datetime", inplace=True)
                df = df.astype(float)
                return df.sort_index()
            else:
                print("⚠️ Fehlerhafte TwelveData-Antwort:", data)
        except Exception as e2:
            print("❌ TwelveData Fehler:", e2)
        return pd.DataFrame()


# === TRAINING ===
async def train_model():
    global training_status
    training_status["running"] = True
    training_status["message"] = "📈 Training gestartet..."
    print(training_status["message"])

    try:
        df = get_forex_data("EURUSD=X", "1mo", "1h")
        if df.empty or len(df) < 10:
            training_status["message"] = "❌ Zu wenige oder keine Daten verfügbar."
            training_status["running"] = False
            return

        df["Target"] = df["Close"].shift(-1)
        X = df[["Open", "High", "Low", "Close"]].iloc[:-1]
        y = df["Target"].iloc[:-1]

        model = LinearRegression()
        model.fit(X, y)

        acc = model.score(X, y)
        training_status["accuracy"] = round(acc * 100, 2)
        training_status["message"] = f"✅ Training fertig: {training_status['accuracy']}%"
        print(training_status["message"])
    except Exception as e:
        training_status["message"] = f"❌ Fehler beim Training: {e}"
        print(training_status["message"])
    finally:
        training_status["running"] = False


# === TELEGRAM COMMANDS ===
async def start(update, context):
    await update.message.reply_text("👋 Monica Option Bot aktiv.\nBefehle: /train /status /predict")

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
    df = get_forex_data("EURUSD=X", "1d", "1h")
    if df.empty:
        await update.message.reply_text("❌ Keine Kursdaten verfügbar.")
        return
    last = df.iloc[-1]
    change = last["Close"] - last["Open"]
    signal = "📈 BUY" if change > 0 else "📉 SELL"
    await update.message.reply_text(f"{signal} — Δ {round(change,5)}")


# === Telegram Handler registrieren ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("train", train))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("predict", predict))


# === WEBHOOK ENDPOINT (Quart) ===
@app.route("/")
async def index():
    return "✅ Monica Option Bot läuft."

@app.route("/webhook", methods=["POST"])
async def webhook():
    data = await request.get_json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "OK"


# === WATCHDOG: automatischer Neustart bei Codeänderung ===
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
            try:
                fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
                fut.result(timeout=5)
            except Exception as e:
                print("Warnung: konnte Restart-Nachricht nicht senden:", e)
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


# === MAIN START ===
async def main():
    print("🚀 Initialisiere Monica Option Bot...")
    await application.initialize()

    webhook_url = f"{RENDER_URL}/webhook"
    await application.bot.set_webhook(webhook_url)
    print(f"✅ Webhook gesetzt: {webhook_url}")

    if CHAT_ID:
        try:
            await application.bot.send_message(chat_id=CHAT_ID, text="✅ Bot gestartet (Quart + Watchdog aktiv).")
        except Exception as e:
            print("Info: Startup-Message fehlgeschlagen:", e)

    loop = asyncio.get_running_loop()
    t = threading.Thread(target=start_watchdog, args=(loop,), daemon=True)
    t.start()

    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    await serve(app, config)


if __name__ == "__main__":
    asyncio.run(main())
