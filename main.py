import os
import asyncio
import threading
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from flask import Flask
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM, Dropout

# ==============================
# 🔑 ENV Variablen / Tokens
# ==============================
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY", "")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)


# ==============================
# 📬 Telegram
# ==============================
def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Kein Telegram-Token oder Chat-ID gesetzt.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
        print(f"📤 Telegram gesendet: {text[:60]}...")
    except Exception as e:
        print("❌ Telegram-Fehler:", e)


# ==============================
# 📡 DATENQUELLEN
# ==============================
def get_from_twelvedata():
    print("📡 Lade EUR/USD von TwelveData...")
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": "EUR/USD", "interval": "5min", "outputsize": 500, "apikey": TWELVEDATA_KEY}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if "values" not in data:
        raise ValueError(f"TwelveData leer oder ungültig: {data}")
    df = pd.DataFrame(data["values"]).astype({"open": float, "high": float, "low": float, "close": float})
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    print(f"✅ {len(df)} Kerzen von TwelveData geladen.")
    return df


def get_from_finnhub():
    print("📡 Lade EUR/USD von Finnhub...")
    url = "https://finnhub.io/api/v1/forex/candle"
    params = {"symbol": "OANDA:EUR_USD", "resolution": "5", "count": 500, "token": FINNHUB_KEY}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if "c" not in data:
        raise ValueError(f"Finnhub leer: {data}")
    df = pd.DataFrame({
        "datetime": pd.to_datetime(data["t"], unit="s"),
        "open": data["o"],
        "high": data["h"],
        "low": data["l"],
        "close": data["c"]
    })
    print(f"✅ {len(df)} Kerzen von Finnhub geladen.")
    return df


def get_forex_data():
    for fn in [get_from_twelvedata, get_from_finnhub]:
        try:
            return fn()
        except Exception as e:
            print(f"⚠️ Fehler bei {fn.__name__}: {e}")
    print("❌ Keine Datenquellen verfügbar!")
    return None


# ==============================
# 📈 TECHNISCHE INDIKATOREN
# ==============================
def add_indicators(df):
    df = df.copy()
    df["EMA_10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA_26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA_10"] - df["EMA_26"]
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["Volatility"] = df["close"].rolling(window=10).std()
    df["ROC"] = df["close"].pct_change(periods=10)
    df.dropna(inplace=True)
    return df


# ==============================
# 🧠 STRATEGIEN
# ==============================
STRATEGIES = {
    "trend_follow": ["close", "EMA_10", "EMA_26", "MACD"],
    "mean_reversion": ["close", "RSI", "Volatility", "ROC"],
    "volatility": ["Volatility", "MACD", "RSI", "ROC"],
    "breakout": ["high", "low", "close", "MACD", "Volatility"]
}


# ==============================
# 🧩 KI-Basisfunktionen
# ==============================
def build_model(input_shape):
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(32),
        Dense(16, activation="relu"),
        Dense(1, activation="sigmoid")
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def prepare_data(df, features):
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df.dropna(inplace=True)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[features])
    X, y = [], []
    window = 10
    for i in range(window, len(scaled)):
        X.append(scaled[i - window:i])
        y.append(df["target"].iloc[i])
    return np.array(X), np.array(y), scaler


def train_strategy(df, name, features):
    X, y, scaler = prepare_data(df, features)
    model_path = os.path.join(MODEL_DIR, f"model_{name}.h5")

    if os.path.exists(model_path):
        print(f"📂 Lade Modell für {name}...")
        model = load_model(model_path)
    else:
        print(f"🧠 Erstelle neues Modell für {name}...")
        model = build_model((X.shape[1], X.shape[2]))

    model.fit(X, y, epochs=3, batch_size=32, verbose=0)
    loss, acc = model.evaluate(X, y, verbose=0)
    model.save(model_path)
    print(f"✅ {name} – Genauigkeit: {acc*100:.2f}%")
    return acc, model, scaler


def predict_next(df, model, scaler, features):
    scaled = scaler.transform(df[features])
    last_seq = scaled[-10:].reshape(1, 10, len(features))
    pred = model.predict(last_seq, verbose=0)[0][0]
    return pred


# ==============================
# 🔁 Haupt-Loop
# ==============================
async def auto_loop():
    while True:
        print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – Starte neuen Lernzyklus...")
        df = get_forex_data()
        if df is not None:
            df = add_indicators(df)

            results = {}
            for name, features in STRATEGIES.items():
                acc, model, scaler = train_strategy(df, name, features)
                prob = predict_next(df, model, scaler, features)
                results[name] = {"acc": acc, "prob": prob}

            best = max(results.items(), key=lambda x: x[1]["acc"])
            best_name, best_data = best

            signal = "📈 BUY" if best_data["prob"] > 0.5 else "📉 SELL"
            msg = (
                f"📊 *Monica Option KI v3 Update*\n\n"
                f"🏆 Beste Strategie: *{best_name}*\n"
                f"🎯 Genauigkeit: {best_data['acc']*100:.2f}%\n"
                f"📈 Signal: {signal}\n"
                f"📊 Wahrscheinlichkeit: {best_data['prob']:.2f}"
            )
            send_telegram_message(msg)
        else:
            send_telegram_message("⚠️ Keine Kursdaten erhalten, Zyklus übersprungen.")

        print("💤 Warte 2 Stunden bis zum nächsten Durchlauf...\n")
        await asyncio.sleep(2 * 60 * 60)


def start_bot():
    asyncio.run(auto_loop())


# ==============================
# 🌐 Flask Keepalive
# ==============================
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ Monica Option KI v3 läuft seit " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    print("🚀 Starte Monica Option KI v3 (Mehrstrategien, 2h-Intervall)...")
    send_telegram_message("🤖 Monica Option KI v3 gestartet – Mehrstrategien aktiviert.")
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
