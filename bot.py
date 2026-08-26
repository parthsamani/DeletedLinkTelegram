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
db.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, title TEXT, owner_id INTEGER, owner_name TEXT, added_on TEXT)")
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

def add_group(chat, user):
    try:
        if chat.type in ['group','supergroup']:
            db.execute("INSERT OR IGNORE INTO groups (chat_id, title, owner_id, owner_name, added_on) VALUES (?,?,?,?,?)",
                       (chat.id, chat.title, user.id, user.first_name, datetime.now().strftime("%d-%m-%Y %H:%M")))
            db.commit()
    except Exception as e:
        logging.error(f"Group DB Error: {e}")

@app.route('/')
def home():
    u = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    g = db.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    return f"Bot Live! Users: {u} | Groups: {g}"

@app.route('/users_list')
def users_list():
    if request.args.get("key")!= "parth2580":
        return "Unauthorized - Wrong Key", 403

    groups = db.execute("SELECT * FROM groups ORDER BY added_on DESC").fetchall()
    users = db.execute("SELECT * FROM users ORDER BY last_seen DESC").fetchall()

    html = f"<h2>Total Groups Using Bot: {len(groups)}</h2><table border=1 cellpadding=5><tr><th>Group ID</th><th>Group Name</th><th>Added By ID</th><th>Added By Name</th><th>Date</th></tr>"
    for r in groups:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
    html += "</table><br><br>"

    html += f"<h2>Total Users: {len(users)}</h2><table border=1 cellpadding=5><tr><th>ID</th><th>Name</th><th>Username</th><th>Msgs</th><th>Last Seen</th></tr>"
    for r in users:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
    html += "</table>"
    return html

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

LINK_RE = re.compile(r"https?://|www\.|t\.me/|telegram\.me|@\w+|discord\.gg", re.I)

async def track_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        add_user(update.message.from_user)
        add_group(update.message.chat, update.message.from_user)

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

        warn_text = f"""
