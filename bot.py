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

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN environment variable is missing"
    )


# ==========================================================
# WARNING COOLDOWN
# ==========================================================

WARNING_COOLDOWN = 300

last_warning_time = {}


# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(
    "ParthTraderAlerts_Bot"
)


# ==========================================================
# FLASK SERVER FOR RENDER
# ==========================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "ParthTraderAlerts Anti-Link Bot is Running!"


@web_app.route("/health")
def health():
    return "OK", 200


def run_web_server():

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    web_app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )


# ==========================================================
# URL DETECTION
# ==========================================================

URL_PATTERN = re.compile(
    r"(?i)"
    r"("
    r"(?:https?://|ftp://|www\.)"
    r"[^\s<>()]+"
    r"|"
    r"(?:[a-z0-9-]+\.)+"
    r"(?:com|net|org|in|io|co|me|info|biz|xyz|"
    r"site|online|app|dev|ai|"
    r"co\.in|org\.in|net\.in|t\.me)"
    r"(?:/[^\s<>()]*)?"
    r")"
)


def has_url(text):

    if not text:
        return False

    return bool(
        URL_PATTERN.search(text)
    )


def has_url_entity(
    message_text,
    entities
):

    if not message_text or not entities:
        return False

    for entity in entities:

        if entity.type in (
            "url",
            "text_link"
        ):
            return True

    return False


def message_contains_hyperlink(message):

    # Normal text
    if message.text:

        if has_url(message.text):
            return True

        if has_url_entity(
            message.text,
            message.entities
        ):
            return True

    # Media caption
    if message.caption:

        if has_url(message.caption):
            return True

        if has_url_entity(
            message.caption,
            message.caption_entities
        ):
            return True

    return False


# ==========================================================
# ADMIN CHECK
# ==========================================================

async def is_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user or not chat:
        return False

    if chat.type == "private":
        return True

    try:

        member = await context.bot.get_chat_member(
            chat_id=chat.id,
            user_id=user.id
        )

        return member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR
        )

    except TelegramError as error:

        logger.warning(
            "Admin check error: %s",
            error
        )

        return False


# ==========================================================
# WARNING COOLDOWN CHECK
# ==========================================================

def can_send_warning(
    chat_id,
    user_id
):

    # Unique cooldown for every user in every group
    cooldown_key = (
        chat_id,
        user_id
    )

    current_time = time.time()

    previous_time = last_warning_time.get(
        cooldown_key
    )

    if previous_time is None:

        last_warning_time[
            cooldown_key
        ] = current_time

        return True

    time_difference = (
        current_time
        - previous_time
    )

    if time_difference >= WARNING_COOLDOWN:

        last_warning_time[
            cooldown_key
        ] = current_time

        return True

    return False


# ==========================================================
# CREATE USER MENTION
# ==========================================================

def create_user_mention(user):

    if not user:
        return "Member"

    if user.username:
        return f"@{user.username}"

    first_name = (
        user.first_name
        or "Member"
    )

    return (
        f'<a href="tg://user?id='
        f'{user.id}'
        f'">{first_name}</a>'
    )


# ==========================================================
# DELETE LINK + SEND WARNING
# ==========================================================

async def remove_hyperlink(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message

    if not message:
        return

    # Only groups
    if message.chat.type not in (
        "group",
        "supergroup"
    ):
        return

    # Ignore messages from bots
    if (
        message.from_user
        and message.from_user.is_bot
    ):
        return

    # Do not delete admin/owner messages
    if await is_admin(
        update,
        context
    ):
        return

    # Check link
    if not message_contains_hyperlink(
        message
    ):
        return

    try:

        # ==========================================
        # DELETE LINK MESSAGE
        # ==========================================

        await message.delete()

        logger.info(
            "Link deleted | Chat: %s | User: %s",
            message.chat.id,
            message.from_user.id
            if message.from_user
            else "unknown"
        )


        # ==========================================
        # SEND WARNING ONLY IF COOLDOWN ALLOWS
        # ==========================================

        if (
            message.from_user
            and can_send_warning(
                message.chat.id,
                message.from_user.id
            )
        ):

            user_mention = (
                create_user_mention(
                    message.from_user
                )
            )

            warning_text = (
                f"⚠️ {user_mention},"
                f" 𝐋𝐢𝐧𝐤𝐬 𝐚𝐫𝐞 𝐧𝐨𝐭 𝐚𝐥𝐥𝐨𝐰𝐞𝐝 𝐡𝐞𝐫𝐞! \n"
                f" ░▒▓▁𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐨𝐥𝐥𝐨𝐰 𝐓𝐡𝐞 𝐆𝐫𝐨𝐮𝐩 𝐑𝐮𝐥𝐞𝐬 𝐚𝐧𝐝 𝐀𝐯𝐨𝐢𝐝 𝐒𝐡𝐚𝐫𝐢𝐧𝐠 𝐒𝐮𝐜𝐡 𝐂𝐨𝐧𝐭𝐞𝐧𝐭.▁▓▒░  \n\n"
                f"— <b>ᴾᵃʳᵗʰᵀʳᵃᵈᵉʳᴬˡᵉʳᵗˢ_ᴮᵒᵗ</b>"
f"꧁TᕼᗩᑎKYOᑌ꧂\n"
            )
            await context.bot.send_message(
                chat_id=message.chat.id,
                text=warning_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            logger.info(
                "Warning sent | Chat: %s | User: %s",
                message.chat.id,
                message.from_user.id
            )

        else:

            logger.info(
                "Warning skipped due to cooldown"
            )


    except Forbidden:

        logger.error(
            "Cannot delete message. "
            "Please make the bot an admin and "
            "enable Delete Messages permission."
        )


    except BadRequest as error:

        logger.error(
            "Telegram error: %s",
            error
        )


    except TelegramError as error:

        logger.error(
            "Telegram API error: %s",
            error
        )


    except Exception as error:

        logger.exception(
            "Unexpected error: %s",
            error
        )


# ==========================================================
# /START COMMAND
# ==========================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_message:
        return

    text = (
        "🔗 <b>ParthTraderAlerts Anti-Link Bot</b>\n\n"
        "This bot automatically removes links "
        "sent by group members.\n\n"
        "⚠️ Members receive a warning when "
        "their link is removed.\n\n"
        "⏱️ Warning cooldown: 60 seconds\n\n"
        "👑 Admin and owner messages are not deleted.\n\n"
        "<b>Setup:</b>\n"
        "1. Add the bot to your group\n"
        "2. Promote it as Admin\n"
        "3. Enable Delete Messages permission\n"
        "4. Done! 🚀"
    )

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML"
    )


# ==========================================================
# /HELP COMMAND
# ==========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_message:
        return

    text = (
        "📌 <b>ParthTraderAlerts Anti-Link Bot</b>\n\n"
        "The bot automatically removes:\n\n"
        "🔗 Website URLs\n"
        "🌐 www links\n"
        "🔒 Hidden hyperlinks\n"
        "📎 Links in media captions\n"
        "✏️ Edited messages containing links\n\n"
        "⚠️ Warning messages have a 60-second "
        "cooldown to prevent spam.\n\n"
        "👑 Admins are exempted."
    )

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML"
    )


# ==========================================================
# MAIN
# ==========================================================

def main():

    # Python 3.14 event-loop fix
    try:

        asyncio.get_event_loop()

    except RuntimeError:

        asyncio.set_event_loop(
            asyncio.new_event_loop()
        )


    # Start Render Web Server
    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    logger.info(
        "Render Web Server Started"
    )


    # Create Telegram Application
    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )


    # ==========================================
    # COMMANDS
    # ==========================================

    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )


    # ==========================================
    # NEW MESSAGES
    # ==========================================

    app.add_handler(
        MessageHandler(
            filters.ALL
            & ~filters.COMMAND,
            remove_hyperlink
        )
    )


    # ==========================================
    # EDITED MESSAGES
    # ==========================================

    app.add_handler(
        MessageHandler(
            filters.UpdateType.EDITED_MESSAGE,
            remove_hyperlink
        )
    )


    # ==========================================
    # START BOT
    # ==========================================

    logger.info(
        "ParthTraderAlerts Anti-Link Bot "
        "Started Successfully"
    )

    logger.info(
        "Warning cooldown: %s seconds",
        WARNING_COOLDOWN
    )


    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False
    )


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    main()
