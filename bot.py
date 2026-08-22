import os, re, logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Live 24x7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

LINK_RE = re.compile(r"https?://|www\.|t\.me/|telegram\.me", re.I)

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return
    if msg.from_user and msg.from_user.is_bot: return
    text = msg.text or msg.caption or ""
    ents = msg.entities or msg.caption_entities or []
    is_link = bool(LINK_RE.search(text)) or any(e.type in ("url","text_link") for e in ents) or ("@" in text and " " not in text)
    if not is_link: return
    try:
        member = await context.bot.get_chat_member(msg.chat_id, msg.from_user.id)
        if member.status in ('administrator','creator'): return
        await msg.delete()
        logging.info("Deleted link")
    except Exception as e:
        logging.error(f"Delete fail: {e}")

def main():
    Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, delete_link))
    logging.info("Starting Polling...")
    application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
