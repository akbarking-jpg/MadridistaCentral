import subprocess
import sys

# Kerakli kutubxonalarni o'rnatish
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])

import os
import json
import base64
import requests
import time
from datetime import datetime

# === SOZLAMALAR ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@Madridista_Central")

CATEGORIES = {
    "#transfer": "Transferlar",
    "#oyin": "O'yinlar",
    "#intervyu": "Intervyular",
    "#klub": "Klub yangiliklari",
    "#castilla": "Castilla",
    "#ayollar": "Ayollar jamoasi",
    "#madridista": "Madridistalar",
}

def detect_category(text):
    text_lower = text.lower()
    for tag, category in CATEGORIES.items():
        if tag in text_lower:
            return category
    return "Yangiliklar"

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "allowed_updates": ["channel_post", "message"]}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=35)
        return r.json()
    except Exception as e:
        print(f"getUpdates xatolik: {e}")
        return {"ok": False}

def get_news_json():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    print(f"GitHub xatolik: {r.status_code}")
    return {"news": []}, None

def update_news_json(news_data, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    content = base64.b64encode(
        json.dumps(news_data, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")
    payload = {
        "message": f"Yangi xabar: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content,
        "sha": sha
    }
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in [200, 201]

def process_message(message):
    text = message.get("text") or message.get("caption") or ""
    if not text:
        return

    chat = message.get("chat", {})
    chat_username = chat.get("username", "")
    channel = CHANNEL_ID.replace("@", "")

    if chat_username.lower() != channel.lower():
        print(f"Boshqa kanal: @{chat_username}, o'tkazildi")
        return

    lines = text.strip().split("\n")
    title = lines[0][:120]
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    category = detect_category(text)
    date = datetime.now().strftime("%Y-%m-%d")

    print(f"Yangi post: {title} | {category}")

    news_data, sha = get_news_json()
    if sha is None:
        return

    new_id = max([n["id"] for n in news_data["news"]], default=0) + 1
    news_data["news"].insert(0, {
        "id": new_id,
        "title": title,
        "category": category,
        "date": date,
        "text": body,
        "image": ""
    })
    news_data["news"] = news_data["news"][:50]

    if update_news_json(news_data, sha):
        print(f"✅ Saytga yuklandi: {title}")
    else:
        print(f"❌ GitHub xatolik!")

def main():
    print(f"🤖 Bot ishga tushdi! Kanal: {CHANNEL_ID}")
    offset = None

    while True:
        try:
            result = get_updates(offset)
            if not result.get("ok"):
                print("Telegram API xatolik, 5 soniya kutilmoqda...")
                time.sleep(5)
                continue

            updates = result.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                if "channel_post" in update:
                    process_message(update["channel_post"])
                elif "message" in update:
                    msg = update["message"]
                    if msg.get("text") == "/start":
                        chat_id = msg["chat"]["id"]
                        requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": "🤍 Madridista Central Bot ishlayapti!"}
                        )
        except Exception as e:
            print(f"Xatolik: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
