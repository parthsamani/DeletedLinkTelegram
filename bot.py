import os
import re
import logging
from flask import Flask, request
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in Render Env")

# Fast URL Detector
URL_PATTERN = re.compile(
    r"(?i)(https?://|www\.|t\.me/|telegram\.me/)[^\s]+"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("ParthTraderAlerts")

# Flask App for Render
flask_app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

async def is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except:
        return False

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg: return
    if msg.chat.type not in ("group", "supergroup"): return
    if msg.from_user and msg.from_user.is_bot: return

    # Admin check
    if await is_admin(update, context):
        return

    text = msg.text or msg.caption or ""
    has_link = False

    if URL_PATTERN.search(text):
        has_link = True
    if msg.entities:
        for e in msg.entities:
            if e.type in ("url", "text_link"):
                has_link = True
    if msg.caption_entities:
        for e in msg.caption_entities:
            if e.type in ("url", "text_link"):
                has_link = True

    if has_link:
        try:
            await msg.delete()
            logger.info(f"DELETED | User: {msg.from_user.id} | Chat: {msg.chat.id}")
        except Exception as e:
            logger.error(f"Delete Failed (Make Bot Admin): {e}")

# Handler
application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, delete_link))

# Routes for Render
@flask_app.route("/")
def home():
    return "ParthTraderAlerts_Bot is Running 24x7!"

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@flask_app.route("/setwebhook")
def set_webhook():
    # Webhook set karne ke liye ek baar is URL ko kholna hai
    import asyncio
    async def set_hook():
        url = os.getenv("RENDER_EXTERNAL_URL")
        if not url:
            return "RENDER_EXTERNAL_URL not found"
        webhook_url = f"{url}/{BOT_TOKEN}"
        await application.bot.set_webhook(webhook_url)
        return f"Webhook set to {webhook_url}"
    return asyncio.run(set_hook())

if __name__ == "__main__":
    # Webhook mode start
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
