import os
import asyncio
from telegram.ext import Application
from hypercorn.asyncio import serve
from hypercorn.config import Config
from flask import Flask

# Flask für Render Health Check
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Monica Option Bot läuft!"

async def run_bot():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("❌ Kein TELEGRAM_TOKEN gefunden! Bitte in Render setzen.")
        return

    app_telegram = Application.builder().token(TOKEN).build()
    await app_telegram.initialize()
    await app_telegram.start()
    await app_telegram.updater.start_polling()
    print("🤖 Telegram Bot läuft...")
    await asyncio.Event().wait()  # läuft unendlich

async def run_web():
    config = Config()
    config.bind = ["0.0.0.0:10000"]
    await serve(app, config)

async def main():
    await asyncio.gather(run_bot(), run_web())

if __name__ == "__main__":
    asyncio.run(main())
