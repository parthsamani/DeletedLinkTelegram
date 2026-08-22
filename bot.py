import os, re, logging, asyncio
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
        if member.status in ('administrator','creator'):
            return
        
        user = msg.from_user
        name = f"@{user.username}" if user.username else user.first_name

        await msg.delete()
        logging.info(f"Deleted link from {name}")

        # Warning message bhejo
        warn_msg = await context.bot.send_message(
            chat_id=msg.chat_id,
            text=f"⚠️ {name} Link share karna mana hai! Aapka message delete kar diya gaya hai.𝐋𝐢𝐧𝐤𝐬 𝐚𝐫𝐞 𝐧𝐨𝐭 𝐚𝐥𝐥𝐨𝐰𝐞𝐝 𝐡𝐞𝐫𝐞!
░▒▓▁𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐨𝐥𝐥𝐨𝐰 𝐓𝐡𝐞 𝐆𝐫𝐨𝐮𝐩 𝐑𝐮𝐥𝐞𝐬 𝐚𝐧𝐝 𝐀𝐯𝐨𝐢𝐝 𝐒𝐡𝐚𝐫𝐢𝐧𝐠 𝐒𝐮𝐜𝐡 𝐂𝐨𝐧𝐭𝐞𝐧𝐭.▁▓▒░

—ᴾᵃʳᵗʰᵀʳᵃᵈᵉʳᴬˡᵉʳᵗˢ_ᴮᵒᵗ꧁TᕼᗩᑎKYOᑌ꧂"
        )
        
        # Warning ko 300 second baad auto delete (chahe to hata sakte ho)
        await asyncio.sleep(300)
        try:
            await warn_msg.delete()
        except:
            pass

    except Exception as e:
        logging.error(f"Fail: {e}")

def main():
    Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, delete_link))
    logging.info("Starting Polling with Warning...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
