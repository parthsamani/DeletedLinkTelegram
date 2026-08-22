import os, re, time, logging, requests
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
URL_PATTERN = re.compile(r"(?i)(https?://|www\.|t\.me/|telegram\.me/)[^\s]+")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

flask_app = Flask(__name__)
last_warning = {}

def is_link(text, entities):
    if text and URL_PATTERN.search(text): return True
    if entities:
        for e in entities:
            if e['type'] in ('url','text_link'): return True
    return False

@flask_app.route("/")
def home(): return "Bot Running OK"

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        msg = data.get("message") or data.get("channel_post")
        if not msg: return "OK", 200
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        if chat.get("type") not in ("group","supergroup"): return "OK", 200
        from_user = msg.get("from", {})
        if from_user.get("is_bot"): return "OK", 200
        user_id = from_user.get("id")

        # admin check
        try:
            r = requests.get(f"{API}/getChatMember", params={"chat_id":chat_id,"user_id":user_id}, timeout=5).json()
            if r.get("ok") and r["result"]["status"] in ("administrator","creator"):
                return "OK", 200
        except: pass

        text = msg.get("text") or msg.get("caption") or ""
        entities = msg.get("entities") or msg.get("caption_entities") or []
        if is_link(text, entities):
            requests.post(f"{API}/deleteMessage", json={"chat_id":chat_id,"message_id":msg.get("message_id")}, timeout=5)
            key=(chat_id,user_id)
            now=time.time()
            if key not in last_warning or now-last_warning[key]>300:
                last_warning[key]=now
                name = f"@{from_user.get('username')}" if from_user.get('username') else from_user.get('first_name','User')
                requests.post(f"{API}/sendMessage", json={"chat_id":chat_id,"text":f"⚠️ {name}, Links are not allowed!"}, timeout=5)
    except Exception as e:
        print(e)
    return "OK", 200

@flask_app.route("/setwebhook")
def setwebhook():
    url = "https://deletedlinktelegram.onrender.com"
    wh = f"{url}/{BOT_TOKEN}"
    requests.get(f"{API}/deleteWebhook", params={"drop_pending_updates":"true"})
    resp = requests.get(f"{API}/setWebhook", params={"url":wh}).json()
    return str(resp)
