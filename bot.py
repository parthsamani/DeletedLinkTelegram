import os, re, logging, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

db = sqlite3.connect("users.db", check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, username TEXT, count INTEGER, last_seen TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, title TEXT, owner_id INTEGER, owner_name TEXT, added_on TEXT)")
db.commit()

def track_user_db(user):
    if not user or user.is_bot: return
    try:
        uid = user.id
        name = user.first_name
        username = f"@{user.username}" if user.username else "No username"
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        cur = db.execute("SELECT count FROM users WHERE id=?", (uid,))
        row = cur.fetchone()
        if row:
            db.execute("UPDATE users SET count=?, last_seen=?, name=?, username=? WHERE id=?", (row[0]+1, now, name, username, uid))
        else:
            db.execute("INSERT INTO users (id, name, username, count, last_seen) VALUES (?,?,?,?,?)", (uid, name, username, 1, now))
        db.commit()
    except Exception as e:
        logging.error(f"Track Error: {e}")

def track_group_db(chat, user):
    try:
        if chat.type in ['group','supergroup']:
            now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            cur = db.execute("SELECT chat_id FROM groups WHERE chat_id=?", (chat.id,))
            if not cur.fetchone():
                db.execute("INSERT INTO groups (chat_id, title, owner_id, owner_name, added_on) VALUES (?,?,?,?,?)",
                           (chat.id, chat.title, user.id, user.first_name, now))
                db.commit()
    except: pass

@app.route('/')
def home():
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    gtotal = db.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    return f"Bot Live! Total Users: {total} | Total Groups: {gtotal}"

@app.route('/users_list')
def users_list():
    from flask import request
    if request.args.get("key")!= "parth2580":
        return "Unauthorized - Wrong Key", 403
    groups = db.execute("SELECT * FROM groups ORDER BY added_on DESC").fetchall()
    rows = db.execute("SELECT * FROM users ORDER BY last_seen DESC").fetchall()
    html = f"<h2>Total Groups Using Bot: {len(groups)}</h2><table border=1 cellpadding=5><tr><th>Group ID</th><th>Group Name</th><th>Added By (ID)</th><th>Added By (Name)</th><th>Date</th></tr>"
    for r in groups:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
    html += "</table><br><br>"
    html += "<h2>Total Users: " + str(len(rows)) + "</h2><table border=1 cellpadding=5><tr><th>ID</th><th>Name</th><th>Username</th><th>Msgs</th><th>Last Seen</th></tr>"
    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
    html += "</table>"
    return html

LINK_RE = re.compile(r"https?://|www\.|t\.me/|telegram\.me|@\w+|discord\.gg", re.I)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

async def track_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        track_user_db(update.message.from_user)
        track_group_db(update.message.chat, update.message.from_user)

async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    if update.message.from_user.is_bot: return
    if update.message.text and update.message.text.startswith("/"): return
    text = (update.message.text or update.message.caption or "").lower()
    ents = update.message.entities or update.message.caption_entities or []
    has_link = bool(LINK_RE.search(text)) or any(e.type in ("url","text_link","mention") for e in ents)
    if not has_link: return
    try:
        member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
        if member.status in ('administrator','creator'): return
        await update.message.delete()
        name = f"@{update.message.from_user.username}" if update.message.from_user.username else update.message.from_user.first_name
        warn_text = (
            f"⚠️ {name} Link share karna mana hai 🪬 Aapka Message delete 🚫 kar diya hai.\n"
            "«•»🔗 Links are not ❌ allowed here!«•» █▄◗Don't send Any Link 🖇️ into This Group.◗▄▌\n"
            
            "░▒▓▁𝐏𝐥𝐞𝐚𝐬𝐞 𝐅𝐨𝐥𝐥𝐨𝐰 𝐓𝐡𝐞 𝐆𝐫𝐨𝐮𝐩 𝐑𝐮𝐥𝐞𝐬 & 𝐀𝐯𝐨𝐢𝐝 𝐒𝐡𝐚𝐫𝐢𝐧𝐠 𝐒𝐮𝐜𝐡 𝐂𝐨𝐧𝐭𝐞𝐧𝐭.▁▓▒░\n"
            "~=❚█═ParthTraderAlerts_Bot═█❚=~꧁TᕼᗩᑎKYOᑌ꧂"
        )
        await context.bot.send_message(chat_id=update.message.chat_id, text=warn_text)
    except Exception as e:
        logging.error(f"Error: {e}")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and str(update.effective_user.id)!= str(ADMIN_ID): return
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    gtotal = db.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    rows = db.execute("SELECT name, username, id, count, last_seen FROM users ORDER BY last_seen DESC LIMIT 10").fetchall()
    msg = f"📊 *Bot Stats*\n\nTotal Groups: *{gtotal}*\nTotal Users: *{total}*\n\n*Last 10 Users:*\n"
    for r in rows:
        msg += f"{r[0]} {r[1]} - `{r[2]}` - {r[3]} msgs - {r[4]}\n"
    msg += f"\nFull list: /users_list?key=parth2580"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user_db(update.effective_user)
    await update.message.reply_text("Welcome! I delete links & keep group clean.")

def main():
    Thread(target=run_flask, daemon=True).start()
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start_cmd))
    app_bot.add_handler(CommandHandler("users", stats_cmd))
    app_bot.add_handler(CommandHandler("stats", stats_cmd))
    app_bot.add_handler(MessageHandler(filters.ALL, track_all_messages), group=-1)
    app_bot.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, delete_link))
    logging.info("Bot Started - No Auto Delete Warning")
    app_bot.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
