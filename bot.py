import os, re, time, asyncio, logging
from flask import Flask, request
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
URL_PATTERN = re.compile(r"(?i)(https?://|www\.|t\.me/|telegram\.me/)[^\s]+")
WARNING_COOLDOWN = 300
last_warning = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Bot")

flask_app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

def can_warn(cid, uid):
    key=(cid,uid); now=time.time()
    if key not in last_warning or now-last_warning[key]>=WARNING_COOLDOWN:
        last_warning[key]=now; return True
    return False

async def is_admin(update, context):
    try:
        m=await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return m.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
    except: return False

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg=update.effective_message
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
            if can_warn(msg.chat.id, msg.from_user.id):
                name = f"@{msg.from_user.username}" if msg.from_user.username else msg.from_user.first_name
                await context.bot.send_message(
                    chat_id=msg.chat.id,
                    text=f"⚠️ {name}, 𝐋𝐢𝐧𝐤𝐬 𝐚𝐫𝐞 𝐧𝐨𝐭 𝐚𝐥𝐥𝐨𝐰𝐞𝐝 𝐡𝐞𝐫𝐞!\n░▒▓▁𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐨𝐥𝐥𝐨𝐰 𝐓𝐡𝐞 𝐆𝐫𝐨𝐮𝐩 𝐑𝐮𝐥𝐞𝐬▁▓▒░",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Delete fail: {e}")

application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, delete_link))

@flask_app.route("/")
def home(): return "Bot Running"

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    await application.initialize()
    await application.start()
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

@flask_app.route("/setwebhook")
async def set_webhook():
    url = os.getenv("RENDER_EXTERNAL_URL")
    webhook_url = f"{url}/{BOT_TOKEN}"
    await application.bot.set_webhook(webhook_url)
    return f"Webhook set to {webhook_url}"

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
