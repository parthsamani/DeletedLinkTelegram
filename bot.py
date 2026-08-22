import os, re, logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

LINK_RE = re.compile(r"https?://|www\.|t\.me/|telegram\.me|@\w+|discord\.gg", re.I)

async def auto_delete_warning(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    try:
        await context.bot.delete_message(job.chat_id, job.data)
    except:
        pass

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user: return
    if msg.from_user.is_bot: return
    if msg.text and msg.text.startswith("/"): return

    text = (msg.text or msg.caption or "").lower()
    ents = msg.entities or msg.caption_entities or []
    has_link = bool(LINK_RE.search(text)) or any(e.type in ("url","text_link","mention") for e in ents)
    
    if not has_link: return

    try:
        member = await context.bot.get_chat_member(msg.chat_id, msg.from_user.id)
        if member.status in ('administrator','creator'): return

        await msg.delete()
        user = msg.from_user
        name = f"@{user.username}" if user.username else user.first_name

        warn_text = f"""⚠️ {name} Link share karna mana hai! Message delete kar diya gaya hai. 🔗 𝐋𝐢𝐧𝐤𝐬 𝐚𝐫𝐞 𝐧𝐨𝐭 𝐚𝐥𝐥𝐨𝐰𝐞𝐝 𝐡𝐞𝐫𝐞!
░▒▓▁𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐨𝐥𝐥𝐨𝐰 𝐓𝐡𝐞 𝐆𝐫𝐨𝐮𝐩 𝐑𝐮𝐥𝐞𝐬 & 𝐀𝐯𝐨𝐢𝐝 𝐒𝐡𝐚𝐫𝐢𝐧𝐠 𝐒𝐮𝐜𝐡 𝐂𝐨𝐧𝐭𝐞𝐧𝐭.▁▓▒░
—ᴾᵃʳᵗʰᵀʳᵃᵈᵉʳᴬˡᵉʳᵗˢ_ᴮᵒᵗ꧁TᕼᗩᑎKYOᑌ꧂"""

        sent = await context.bot.send_message(chat_id=msg.chat_id, text=warn_text)
        # 300 sec = 5 minute baad auto delete
        context.job_queue.run_once(auto_delete_warning, 300, chat_id=msg.chat_id, data=sent.message_id)
        
    except Exception as e:
        logging.error(f"Error: {e}")

def main():
    Thread(target=run_flask, daemon=True).start()
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, delete_link))
    logging.info("Polling Started - 5 min auto delete")
    app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
