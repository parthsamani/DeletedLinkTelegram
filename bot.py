import os, asyncio, logging, re
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in Render Environment!")

logging.basicConfig(level=logging.INFO)

# --- Flask for UptimeRobot (Render needs PORT) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Live 24x7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# --- Link Detector ---
LINK_REGEX = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/)", re.I)

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return
    # Bot ke message ignore
    if msg.from_user and msg.from_user.is_bot: return
    
    text = (msg.text or msg.caption or "")
    entities = msg.entities or msg.caption_entities or []
    
    is_link = False
    if LINK_REGEX.search(text): is_link = True
    for e in entities:
        if e.type in ("url","text_link"): is_link = True

    if is_link:
        try:
            # Check if sender is admin
            member = await context.bot.get_chat_member(msg.chat_id, msg.from_user.id)
            if member.status in ('administrator','creator'):
                return

            await msg.delete()
            logging.info(f"Deleted link from {msg.from_user.id}")
        except Exception as e:
            logging.error(f"Delete failed (Is bot admin with Delete permission?): {e}")

async def main():
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, delete_link))
    
    # Purana webhook hatao, polling start karo
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
