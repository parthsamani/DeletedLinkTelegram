import os, re, logging, asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)
logging.info(f"Bot Token Loaded: {BOT_TOKEN[:4]}...")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_flask, daemon=True).start()

LINK_RE = re.compile(r"https?://|www\.|t\.me/|telegram\.me", re.I)

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return
    if msg.from_user and msg.from_user.is_bot: return
    text = msg.text or msg.caption or ""
    if not LINK_RE.search(text) and "@" not in text:
        # entities bhi check karo
        ents = msg.entities or []
        if not any(e.type in ("url","text_link") for e in ents):
            return
    try:
        # admin check
        member = await context.bot.get_chat_member(msg.chat_id, msg.from_user.id)
        if member.status in ('administrator','creator'):
            return
        await msg.delete()
        logging.info("Deleted link")
    except Exception as e:
        logging.error(f"Delete failed: {e}")

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, delete_link))
    # Important: webhook hatao
    await application.bot.delete_webhook(drop_pending_updates=True)
    logging.info("Starting Polling...")
    await application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
