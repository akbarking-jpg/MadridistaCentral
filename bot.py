import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])

import os
import json
import base64
import requests
import time
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@Madridista_Central").replace("@", "")

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
    for tag, cat in CATEGORIES.items():
        if tag in text.lower():
            return cat
    return "Yangiliklar"

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 20}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=25)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Telegram status: {r.status_code} — {r.text[:200]}")
            return {"ok": False}
    except Exception as e:
        print(f"getUpdates xatolik: {e}")
        return {"ok": False}

def get_news_json():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(content), data["sha"]
        print(f"GitHub xatolik: {r.status_code}")
    except Exception as e:
        print(f"GitHub error: {e}")
    return {"news": []}, None

def update_news_json(news_data, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json"}
    content = base64.b64encode(
        json.dumps(news_data, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")
    payload = {
        "message": f"Yangi xabar: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content,
        "sha": sha
    }
    try:
        r = requests.put(url, headers=headers, json=payload, timeout=10)
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"Update error: {e}")
        return False

def process_post(message):
    text = message.get("text") or message.get("caption") or ""
    if not text.strip():
        return

    chat_username = message.get("chat", {}).get("username", "")
    if chat_username.lower() != CHANNEL_ID.lower():
        print(f"Boshqa kanal: @{chat_username}")
        return

    lines = text.strip().split("\n")
    title = lines[0][:120]
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    category = detect_category(text)
    date = datetime.now().strftime("%Y-%m-%d")

    print(f"Post keldi: [{category}] {title}")

    news_data, sha = get_news_json()
    if not sha:
        print("SHA topilmadi!")
        return

    new_id = max([n["id"] for n in news_data.get("news", [])], default=0) + 1
    news_data.setdefault("news", []).insert(0, {
        "id": new_id, "title": title, "category": category,
        "date": date, "text": body, "image": ""
    })
    news_data["news"] = news_data["news"][:50]

    if update_news_json(news_data, sha):
        print(f"✅ Saytga yuklandi: {title}")
    else:
        print("❌ GitHub xatolik!")

def main():
    print(f"🤖 Bot ishga tushdi! Kanal: @{CHANNEL_ID}")
    print(f"Token: {TELEGRAM_BOT_TOKEN[:10]}...")

    # Webhook ni o'chirish (conflict oldini olish)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook",
            json={"drop_pending_updates": False},
            timeout=10
        )
        print(f"Webhook o'chirildi: {r.json()}")
    except Exception as e:
        print(f"Webhook xatolik: {e}")

    offset = None
    while True:
        result = get_updates(offset)
        if not result.get("ok"):
            print("API xatolik, 10 soniya kutilmoqda...")
            time.sleep(10)
            continue

        updates = result.get("result", [])
        if updates:
            print(f"{len(updates)} ta yangilanish keldi")

        for update in updates:
            offset = update["update_id"] + 1
            if "channel_post" in update:
                process_post(update["channel_post"])

if __name__ == "__main__":
    main()
