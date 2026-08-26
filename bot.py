import os, re, logging, sqlite3
from flask import Flask, request
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- TRACKING SYSTEM DB SETUP ---
db = sqlite3.connect("users.db", check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, username TEXT, count INTEGER, last_seen TEXT)")
db.commit()

def add_user(user):
    try:
        db.execute("INSERT OR IGNORE INTO users (id, name, username, count, last_seen) VALUES (?,?,?, 0,?)",
                   (user.id, user.first_name, user.username or "", datetime.now().strftime("%d-%m-%Y %H:%M")))
        db.execute("UPDATE users SET count = count + 1, last_seen =? WHERE id =?",
                   (datetime.now().strftime("%d-%m-%Y %H:%M"), user.id))
        db.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")

@app.route('/')
def home(): return "Bot Live!"

@app.route('/users_list')
def users_list():
    # Password protection - link aise khulega /users_list?key=parth123
    if request.args.get("key")!= "parth2580":
        return "Unauthorized - Wrong Key", 403

    rows = db.execute("SELECT * FROM users ORDER BY last_seen DESC").fetchall()
    html = f"<h2>Total Users: {len(rows)}</h2><table border=1 cellpadding=5><tr><th>ID</th><th>Name</th><th>Username</th><th>Msgs</th><th>Last Seen</th></tr>"
    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
    html += "</table>"
    return html

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

LINK_RE = re.compile(r"https?://|www\.|t\.me/|telegram\.me|@\w+|discord\.gg", re.I)

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.from_user: return
    if msg.from_user.is_bot: return
    if msg.text and msg.text.startswith("/"): return

    # Tracking call
    add_user(msg.from_user)

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

        # Warning delete nahi hoga ab
        await context.bot.send_message(chat_id=msg.chat_id, text=warn_text)

    except Exception as e:
        logging.error(f"Error: {e}")

def main():
    Thread(target=run_flask, daemon=True).start()
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, delete_link))
    logging.info("Polling Started - Warning will NOT auto delete")
    app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
