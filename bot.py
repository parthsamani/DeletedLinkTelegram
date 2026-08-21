import asyncio
import logging
import os
import re
import threading
import time
from flask import Flask
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")

WARNING_COOLDOWN = 300
last_warning_time = {}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ParthTraderAlerts_Bot")

# --- FLASK FOR RENDER 24x7 ---
web_app = Flask(__name__)
@web_app.route("/")
def home(): return "ParthTraderAlerts Anti-Link Bot is Running!"
@web_app.route("/health")
def health(): return "OK", 200

def run_web_server():
    port = int(os.environ.get("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- FAST URL DETECTION ---
URL_PATTERN = re.compile(r"(?i)((?:https?://|ftp://|www\.)[^\s<>()]+|(?:[a-z0-9-]+\.)+(?:com|net|org|in|io|co|me|info|biz|xyz|site|online|app|dev|ai|co\.in|t\.me)(?:/[^\s<>()]*)?)")

def has_url(text): return bool(text and URL_PATTERN.search(text))
def has_url_entity(text, entities):
    if not text or not entities: return False
    return any(e.type in ("url", "text_link") for e in entities)

def message_contains_hyperlink(message):
    if message.text and (has_url(message.text) or has_url_entity(message.text, message.entities)): return True
    if message.caption and (has_url(message.caption) or has_url_entity(message.caption, message.caption_entities)): return True
    return False

# --- ADMIN CHECK WITH CACHE (Fast) ---
admin_cache = {}
async def is_admin(update, context):
    msg, user, chat = update.effective_message, update.effective_user, update.effective_chat
    if not msg or not user or not chat: return False
    if chat.type == "private": return True
    try:
        # 5 min cache for speed
        key = (chat.id, user.id)
        if key in admin_cache and time.time() - admin_cache[key][1] < 300:
            return admin_cache[key][0]
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_adm = member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
        admin_cache[key] = (is_adm, time.time())
        return is_adm
    except: return False

def can_send_warning(chat_id, user_id):
    key = (chat_id, user_id)
    now = time.time()
    if key not in last_warning_time or now - last_warning_time[key] >= WARNING_COOLDOWN:
        last_warning_time[key] = now
        return True
    return False

def create_user_mention(user):
    if not user: return "Member"
    if user.username: return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{user.first_name or "Member"}</a>'

# --- MAIN DELETE LOGIC (SUPER FAST) ---
async def remove_hyperlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or message.chat.type not in ("group", "supergroup"): return
    if message.from_user and message.from_user.is_bot: return
    if await is_admin(update, context): return
    if not message_contains_hyperlink(message): return

    try:
        # INSTANT DELETE - No delay
        await message.delete()
        logger.info(f"Deleted link | Chat: {message.chat.id} | User: {message.from_user.id}")

        if message.from_user and can_send_warning(message.chat.id, message.from_user.id):
            warning_text = (
                f"⚠️ {create_user_mention(message.from_user)}, "
                f"𝐋𝐢𝐧𝐤𝐬 𝐚𝐫𝐞 𝐧𝐨𝐭 𝐚𝐥𝐥𝐨𝐰𝐞𝐝 𝐡𝐞𝐫𝐞!\n"
                f"░▒▓▁𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐨𝐥𝐥𝐨𝐰 𝐓𝐡𝐞 𝐆𝐫𝐨𝐮𝐩 𝐑𝐮𝐥𝐞𝐬 & 𝐀𝐯𝐨𝐢𝐝 𝐒𝐡𝐚𝐫𝐢𝐧𝐠 𝐒𝐮𝐜𝐡 𝐂𝐨𝐧𝐭𝐞𝐧𝐭.▁▓▒░\n\n"
                f"—<b>ᴾᵃʳᵗʰᵀʳᵃᵈᵉʳᴬˡᵉʳᵗˢ_ᴮᵒᵗ</b>꧁TᕼᗩᑎKYOᑌ꧂"
            )
            await context.bot.send_message(chat_id=message.chat.id, text=warning_text, parse_mode="HTML", disable_web_page_preview=True)
    except Forbidden:
        logger.error("Bot is not admin with Delete permission!")
    except Exception as e:
        logger.error(f"Error: {e}")

async def start_command(update, context):
    await update.effective_message.reply_text("🔗 <b>ParthTraderAlerts Anti-Link Bot</b>\n\nBot 24x7 Active hai! Link bhejte hi delete hoga.\n\n👑 Admins are safe.", parse_mode="HTML")

async def help_command(update, context):
    await update.effective_message.reply_text("📌 Bot removes all links, t.me links, www links instantly.", parse_mode="HTML")

def main():
    # Fix for Python 3.12+
    try: asyncio.get_event_loop()
    except RuntimeError: asyncio.set_event_loop(asyncio.new_event_loop())

    threading.Thread(target=run_web_server, daemon=True).start()
    logger.info("Render Web Server Started")

    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # FIXED: Edited message handler sahi kiya
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, remove_hyperlink))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED, remove_hyperlink))

    logger.info("Bot Started Successfully - 24x7 Mode")
    # drop_pending_updates=True se fast start hoga
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    # 24x7 Auto-Restart Loop - Kabhi band nahi hoga
    while True:
        try:
            main()
        except Exception as e:
            logger.exception(f"Bot crashed, restarting in 5s: {e}")
            time.sleep(5)
