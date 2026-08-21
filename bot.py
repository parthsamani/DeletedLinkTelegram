import os
import re
import time
import logging
from flask import Flask, request
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

URL_PATTERN = re.compile(r"(?i)(https?://|www\.|t\.me/|telegram\.me/)[^\s]+")
WARNING_COOLDOWN = 300 # 5 min me ek hi baar warning
last_warning = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ParthTraderAlerts")

flask_app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

def can_warn(chat_id, user_id):
    key = (chat_id, user_id)
    now = time.time()
    if key not in last_warning or now - last_warning[key] >= WARNING_COOLDOWN:
        last_warning[key] = now
        return True
    return False

async def is_admin(update, context):
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return m.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except: return False

def mention(user):
    if not user: return "Member"
    if user.username: return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or msg.chat.type not in ("group","supergroup"): return
    if msg.from_user and msg.from_user.is_bot: return
    if await is_admin(update, context): return

    text = msg.text or msg.caption or ""
    has_link = bool(URL_PATTERN.search(text))

    if not has_link and msg.entities:
        has_link = any(e.type in ("url","text_link") for e in msg.entities)
    if not has_link and msg.caption_entities:
        has_link = any(e.type in ("url","text_link") for e in msg.caption_entities)

    if has_link:
        try:
            await msg.delete()
            logger.info(f"Deleted link from {msg.from_user.id}")

            # WARNING WITH COOLDOWN
            if can_warn(msg.chat.id, msg.from_user.id):
                warn_text = (
                    f"⚠️ {mention(msg.from_user)}, 𝐋𝐢𝐧𝐤𝐬 𝐚𝐫𝐞 𝐧𝐨𝐭 𝐚𝐥𝐥𝐨𝐰𝐞𝐝 𝐡𝐞𝐫𝐞!\n"
                    f"░▒▓▁𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐨𝐥𝐥𝐨𝐰 𝐓𝐡𝐞 𝐆𝐫𝐨𝐮𝐩 𝐑𝐮𝐥𝐞𝐬 𝐚𝐧𝐝 𝐀𝐯𝐨𝐢𝐝 𝐒𝐡𝐚𝐫𝐢𝐧𝐠 𝐒𝐮𝐜𝐡 𝐂𝐨𝐧𝐭𝐞𝐧𝐭.▁▓▒░\n\n"
                    f"—<b>ᴾᵃʳᵗʰᵀʳᵃᵈᵉʳᴬˡᵉʳᵗˢ_ᴮᵒᵗ</b>꧁TᕼᗩᑎKYOᑌ꧂"
                )
                await context.bot.send_message(
                    chat_id=msg.chat.id, text=warn_text,
                    parse_mode="HTML", disable_web_page_preview=True
                )
        except Exception as e:
            logger.error(f"Delete failed: {e}")

application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, delete_link))

@flask_app.route("/")
def home(): return "Bot Running 24x7!"

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@flask_app.route("/setwebhook")
def set_webhook():
    import asyncio
    async def set_hook():
        url = os.getenv("RENDER_EXTERNAL_URL")
        webhook_url = f"{url}/{BOT_TOKEN}"
        await application.bot.set_webhook(webhook_url)
        return f"Webhook set to {webhook_url}"
    return asyncio.run(set_hook())

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
