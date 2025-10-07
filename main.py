import os
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === Telegram Token ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# === URL deines Render-KI-Servers ===
TRAIN_SERVER_URL = "https://monica-option-train.onrender.com"

# === Telegram Bot Befehle ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Willkommen beim *Monica Option KI-Bot!*\n\n"
        "Verfügbare Befehle:\n"
        "• /status – Zeigt den aktuellen KI-Trainingsstatus\n"
        "• /train – Startet ein neues Training\n"
        "• /help – Zeigt diese Hilfe\n\n"
        "🌐 Verbunden mit Render: " + TRAIN_SERVER_URL,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 *Hilfe – Monica Option Bot*\n\n"
        "• /status – Zeigt den Trainingsstatus der KI\n"
        "• /train – Startet das KI-Training manuell\n"
        "• /help – Diese Übersicht anzeigen",
        parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fragt den Render-Server nach dem aktuellen KI-Status ab"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{TRAIN_SERVER_URL}/status") as response:
                data = await response.json()
                msg = (
                    f"📊 *KI-Status:*\n"
                    f"🧠 Training aktiv: {data.get('is_training', False)}\n"
                    f"💬 Nachricht: {data.get('message', 'Keine Daten')}"
                )
        except Exception as e:
            msg = f"⚠️ Fehler beim Abrufen des Status:\n`{e}`"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Startet das Training auf Render"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{TRAIN_SERVER_URL}/start_training") as response:
                data = await response.json()
                msg = f"🚀 {data.get('message', 'Training gestartet!')}"
        except Exception as e:
            msg = f"⚠️ Fehler beim Starten des Trainings:\n`{e}`"
    await update.message.reply_text(msg, parse_mode="Markdown")


# === Hauptfunktion ===

async def main():
    print("✅ Monica Option Bot startet...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Befehle registrieren
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("train", train))

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
