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
MODEL_PATH = "model_eurusd.h5"

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

def get_from_alphavantage():
    print("📡 Lade EUR/USD von AlphaVantage...")
    url = "https://www.alphavantage.co/query"
    params = {"function": "FX_INTRADAY", "from_symbol": "EUR", "to_symbol": "USD", "interval": "5min", "apikey": ALPHAVANTAGE_KEY}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if "Time Series FX (5min)" not in data:
        raise ValueError(f"AlphaVantage leer: {data}")
    df = pd.DataFrame.from_dict(data["Time Series FX (5min)"], orient="index")
    df = df.rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close"
    }).astype(float)
    df["datetime"] = pd.to_datetime(df.index)
    df = df.sort_values("datetime")
    print(f"✅ {len(df)} Kerzen von AlphaVantage geladen.")
    return df

def get_forex_data():
    dfs = []
    for fn in [get_from_twelvedata, get_from_finnhub, get_from_alphavantage]:
        try:
            df = fn()
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ Fehler bei {fn.__name__}: {e}")
    if not dfs:
        print("❌ Keine Datenquellen verfügbar!")
        return None
    df_merged = pd.concat(dfs).groupby("datetime").mean().reset_index().sort_values("datetime")
    print(f"📊 Kombinierte Datensätze: {len(df_merged)} Kerzen.")
    return df_merged

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
    df = df.dropna()
    return df

# ==============================
# 🧠 KI-TRAINING
# ==============================
def build_model(input_shape):
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        Dropout(0.3),
        LSTM(64),
        Dense(32, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def prepare_data(df):
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df.dropna(inplace=True)
    feature_cols = ["open", "high", "low", "close", "EMA_10", "EMA_26", "MACD", "RSI", "Volatility", "ROC"]
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[feature_cols])
    X, y = [], []
    window = 10
    for i in range(window, len(scaled)):
        X.append(scaled[i-window:i])
        y.append(df["target"].iloc[i])
    return np.array(X), np.array(y), scaler

def train_model(df):
    X, y, _ = prepare_data(df)
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
    return acc, model

def predict_next(df, model):
    _, _, scaler = prepare_data(df)
    scaled = scaler.transform(df[["open", "high", "low", "close", "EMA_10", "EMA_26", "MACD", "RSI", "Volatility", "ROC"]])
    last_seq = scaled[-10:].reshape(1, 10, 10)
    pred = model.predict(last_seq)[0][0]
    signal = "📈 BUY" if pred > 0.5 else "📉 SELL"
    rsi, macd, ema = df["RSI"].iloc[-1], df["MACD"].iloc[-1], df["EMA_10"].iloc[-1]
    print(f"🤖 Prognose: {signal} ({pred:.2f}) | RSI={rsi:.1f}, MACD={macd:.5f}, EMA={ema:.5f}")
    return signal, pred, rsi, macd, ema

# ==============================
# 🔁 Hintergrund-Loop
# ==============================
async def auto_loop():
    while True:
        print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – Starte neuen Lernzyklus...")
        df = get_forex_data()
        if df is not None:
            df = add_indicators(df)
            acc, model = train_model(df)
            signal, prob, rsi, macd, ema = predict_next(df, model)
            msg = (
                f"📊 *Monica Option KI Update*\n\n"
                f"🎯 Genauigkeit: {acc*100:.2f}%\n"
                f"{signal}\n"
                f"📊 Wahrscheinlichkeit: {prob:.2f}\n"
                f"📉 RSI: {rsi:.1f} | MACD: {macd:.5f} | EMA10: {ema:.5f}"
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
    return "✅ Monica Option Bot läuft seit " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    print("🚀 Starte Monica Option KI v2.1 (Render-kompatibel ohne Konflikte)...")
    send_telegram_message("🤖 Monica Option KI v2.1 gestartet (Render-kompatibel).")
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
