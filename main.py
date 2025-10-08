import os
import asyncio
import requests
from datetime import datetime

# ==============================
# 🔑 API Keys (aus Umgebungsvariablen oder .env)
# ==============================
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY", "")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")

# ==============================
# 📡 Datenquellen
# ==============================

def get_from_finnhub():
    print("📡 Lade EUR/USD von Finnhub.io...")
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
    if not data or "c" not in data or len(data["c"]) == 0:
        raise ValueError("⚠️ Finnhub leer oder ungültig")
    print("✅ Finnhub-Daten empfangen.")
    return data


def get_from_twelvedata():
    print("📡 Lade EUR/USD von TwelveData...")
    url = f"https://api.twelvedata.com/time_series"
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
        raise ValueError("⚠️ TwelveData leer oder ungültig")
    print("✅ TwelveData-Daten empfangen.")
    return data


def get_from_alphavantage():
    print("📡 Lade EUR/USD von AlphaVantage...")
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "FX_INTRADAY",
        "from_symbol": "EUR",
        "to_symbol": "USD",
        "interval": "5min",
        "apikey": ALPHAVANTAGE_KEY,
        "outputsize": "full"
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    if "Time Series FX (5min)" not in data:
        raise ValueError("⚠️ AlphaVantage leer oder ungültig")
    print("✅ AlphaVantage-Daten empfangen.")
    return data


def get_forex_data():
    """Automatisches Fallback-System"""
    try:
        return get_from_finnhub()
    except Exception as e1:
        print("⚠️ Finnhub-Fehler:", e1)
        try:
            return get_from_twelvedata()
        except Exception as e2:
            print("⚠️ TwelveData-Fehler:", e2)
            try:
                return get_from_alphavantage()
            except Exception as e3:
                print("❌ Alle Quellen fehlgeschlagen:", e3)
                return None

# ==============================
# 🧠 Selbstlern-System (Platzhalter)
# ==============================

def train_model(data):
    """Hier entwickelt sich dein Bot selbst weiter"""
    print("🧠 Trainiere Modell mit neuen Daten...")
    # Beispiel: Durchschnitt oder Musteranalyse
    closes = []
    if "c" in data:  # Finnhub
        closes = data["c"]
    elif "values" in data:  # TwelveData
        closes = [float(v["close"]) for v in data["values"]]
    elif "Time Series FX (5min)" in data:  # AlphaVantage
        closes = [float(v["4. close"]) for v in data["Time Series FX (5min)"].values()]
    
    if not closes:
        print("⚠️ Keine Schlusskurse gefunden.")
        return

    avg = sum(closes[-100:]) / min(100, len(closes))
    print(f"📊 Durchschnitt der letzten 100 Werte: {avg:.5f}")
    print("✅ Training abgeschlossen (Modell-Update gespeichert).")


# ==============================
# 🔁 Automatische Aktualisierung
# ==============================

async def auto_update():
    while True:
        print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – Starte neuen Datenzyklus...")
        data = get_forex_data()
        if data:
            train_model(data)
        else:
            print("⚠️ Keine Daten empfangen, überspringe Zyklus.")
        print("💤 Warte 6 Stunden bis zum nächsten Update...\n")
        await asyncio.sleep(6 * 60 * 60)  # 6 Stunden


# ==============================
# 🚀 Startpunkt
# ==============================

if __name__ == "__main__":
    print("🚀 Starte selbstlernende Forex-KI...")
    asyncio.run(auto_update())
