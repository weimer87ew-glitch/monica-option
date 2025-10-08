import os
import asyncio
import requests
import numpy as np
import pandas as pd
from datetime import datetime
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

MODEL_PATH = "model_eurusd.h5"


# ==============================
# 📬 Telegram
# ==============================

def send_telegram_message(text):
    """Sendet eine Nachricht an Telegram (Bot → Chat-ID)"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Kein Telegram-Token oder Chat-ID gesetzt.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text})
        print(f"📤 Telegram gesendet: {text[:60]}...")
    except Exception as e:
        print("❌ Telegram-Fehler:", e)


# ==============================
# 📡 DATENQUELLEN
# ==============================

def get_from_twelvedata():
    print("📡 Lade EUR/USD von TwelveData...")
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "EUR/USD",
        "interval": "5min",
        "outputsize": 500,
        "apikey": TWELVEDATA_KEY
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if "values" not in data:
        raise ValueError(f"TwelveData leer oder ungültig: {data}")
    df = pd.DataFrame(data["values"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float})
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    print(f"✅ {len(df)} Kerzen geladen.")
    return df


def get_from_finnhub():
    print("📡 Lade EUR/USD von Finnhub...")
    url = "https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": "OANDA:EUR_USD",
        "resolution": "5",
        "count": 500,
        "token": FINNHUB_KEY
    }
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
    print(f"✅ {len(df)} Kerzen geladen.")
    return df


def get_forex_data():
    try:
        return get_from_twelvedata()
    except Exception as e:
        print("⚠️ TwelveData-Fehler:", e)
        try:
            return get_from_finnhub()
        except Exception as e2:
            print("⚠️ Finnhub-Fehler:", e2)
            return None


# ==============================
# 🧠 KI-TRAINING
# ==============================

def build_model(input_shape):
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(32),
        Dense(16, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model


def prepare_data(df):
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df.dropna(inplace=True)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[["open", "high", "low", "close"]])
    X, y = [], []
    window = 10
    for i in range(window, len(scaled)):
        X.append(scaled[i-window:i])
        y.append(df["target"].iloc[i])
    return np.array(X), np.array(y)


def train_model(df):
    X, y = prepare_data(df)
    print(f"🧩 Trainingsdaten: {X.shape}, Targets: {y.shape}")

    if os.path.exists(MODEL_PATH):
        print("📂 Lade bestehendes Modell...")
        model = load_model(MODEL_PATH)
    else:
        print("🧠 Erstelle neues Modell...")
        model = build_model((X.shape[1], X.shape[2]))

    model.fit(X, y, epochs=5, batch_size=32, verbose=1)
    loss, acc = model.evaluate(X, y, verbose=0)
    print(f"✅ Training abgeschlossen – Genauigkeit: {acc*100:.2f}%")

    model.save(MODEL_PATH)
    print("💾 Modell gespeichert.")
    return acc


def predict_next(df):
    if not os.path.exists(MODEL_PATH):
        print("⚠️ Kein Modell vorhanden.")
        return None

    model = load_model(MODEL_PATH)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[["open", "high", "low", "close"]])
    last_seq = scaled[-10:].reshape(1, 10, 4)
    pred = model.predict(last_seq)[0][0]
    signal = "📈 BUY" if pred > 0.5 else "📉 SELL"
    print(f"🤖 Prognose: {signal} ({pred:.2f})")
    return signal, pred


# ==============================
# 🔁 Automatischer Ablauf
# ==============================

async def auto_loop():
    while True:
        print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – Starte neuen Lernzyklus...")
        df = get_forex_data()
        if df is not None:
            acc = train_model(df)
            signal, prob = predict_next(df)
            msg = f"📊 *Monica Option KI Update*\n\n🎯 Genauigkeit: {acc*100:.2f}%\n📈 Signal: {signal}\n📊 Wahrscheinlichkeit: {prob:.2f}"
            send_telegram_message(msg)
        else:
            send_telegram_message("⚠️ Keine Kursdaten erhalten, Zyklus übersprungen.")
        print("💤 Warte 6 Stunden bis zum nächsten Durchlauf...\n")
        await asyncio.sleep(6 * 60 * 60)


# ==============================
# 🚀 Start
# ==============================

if __name__ == "__main__":
    print("🚀 Starte Monica Option KI mit Telegram-Updates...")
    send_telegram_message("🤖 Monica Option KI gestartet – bereit für Training & Signale.")
    asyncio.run(auto_loop())
