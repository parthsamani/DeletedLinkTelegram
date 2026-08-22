import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN") # Render me Environment Variable me daalo
# Ye bot turant delete karega

logging.basicConfig(level=logging.INFO)

# --- 1. Health Server for Render 24x7 (Important) ---
app = Flask('')
@app.route('/')
def home():
    return "ParthTraderAlerts_Bot is Live 24x7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. Link Detector & Deleter (Fastest) ---
async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    text = update.message.text or update.message.caption or ""
    
    # Link check - fastest
    if "http://" in text or "https://" in text or "t.me/" in text or "telegram.me" in text or "@" in text and " " not in text:
        try:
            # Direct delete, no delay
            await update.message.delete()
            logging.info(f"Deleted link from {update.message.from_user.id}")
        except Exception as e:
            # Admin nahi hai to fail hoga
            logging.error(f"Delete failed: {e}. Make bot ADMIN!")

# --- 3. Main Bot Runner with Auto-Restart ---
async def main():
    keep_alive() # Render ko jagaye rakhega
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Saare messages par nazar
    application.add_handler(MessageHandler(filters.ALL, delete_link))
    
    # Polling with no delay
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        drop_pending_updates=True, # Purane messages ignore, naye par tez kaam
        allowed_updates=Update.ALL_TYPES
    )
    logging.info("ParthTraderAlerts_Bot Started - Link Deletion Active")
    await application.updater.idle()

if __name__ == "__main__":
    # Loop crash ho to auto restart
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            logging.error(f"Bot crashed, restarting in 5 sec: {e}")
            import time
            time.sleep(5)
