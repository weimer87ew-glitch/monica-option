import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Flask App
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Monica Option Bot läuft!"

# === BOT TOKEN UND URL ===
TOKEN = "8228792401:AAErviwIbHLCLQL2ybraKO-d08pbS_GFMhk"  # ⬅️ Hier deinen echten Token einsetzen!
BOT_URL = "https://monica-option.onrender.com"

# === Telegram Application ===
application = Application.builder().token(TOKEN).build()

# === Einfacher /start Command ===
async def start(update: Update, context):
    await update.message.reply_text("👋 Hallo! Monica Option Bot ist aktiv!")

application.add_handler(CommandHandler("start", start))

# === GLOBALER LOOP ===
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# === Webhook Endpoint ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    loop.create_task(application.process_update(update))  # <-- globaler Loop, kein Fehler!
    return "OK", 200

# === BOT STARTEN ===
async def run_bot():
    await application.initialize()
    await application.bot.set_webhook(url=f"{BOT_URL}/{TOKEN}")
    print("✅ Webhook erfolgreich gesetzt!")
    print("🤖 Monica Option Bot ist bereit.")
    await asyncio.Event().wait()  # hält ihn am Laufen

async def run_web():
    config = Config()
    config.bind = ["0.0.0.0:10000"]
    await serve(app, config)

async def main():
    await asyncio.gather(run_bot(), run_web())

if __name__ == "__main__":
    loop.run_until_complete(main())
