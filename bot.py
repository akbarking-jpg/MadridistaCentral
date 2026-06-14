import os
import json
import base64
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# === SOZLAMALAR ===
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # masalan: @Madridista_Central

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
    print(f"GitHub dan news.json olib bo'lmadi: {r.status_code}")
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
    print(f"GitHub update status: {r.status_code}")
    return r.status_code in [200, 201]

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kanal postini olish
    message = update.channel_post
    if not message:
        return

    print(f"Kanal posti keldi: {message.chat.username} / {message.chat.id}")

    # Faqat o'z kanalimizdan
    if CHANNEL_ID:
        channel = CHANNEL_ID.replace("@", "")
        if message.chat.username and message.chat.username.lower() != channel.lower():
            print(f"Boshqa kanal, o'tkazib yuborildi: {message.chat.username}")
            return

    # Matn yo'q bo'lsa o'tkazib yubor
    if not message.text and not message.caption:
        return

    text = message.text or message.caption or ""
    lines = text.strip().split("\n")
    title = lines[0][:120]
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    category = detect_category(text)
    date = datetime.now().strftime("%Y-%m-%d")

    print(f"Yangilik: {title} | Kategoriya: {category}")

    # news.json ni olish
    news_data, sha = get_news_json()
    if sha is None:
        print("SHA topilmadi, xatolik!")
        return

    # Yangi ID
    new_id = max([n["id"] for n in news_data["news"]], default=0) + 1

    # Yangi yangilik
    new_item = {
        "id": new_id,
        "title": title,
        "category": category,
        "date": date,
        "text": body,
        "image": ""
    }

    news_data["news"].insert(0, new_item)
    news_data["news"] = news_data["news"][:50]

    if update_news_json(news_data, sha):
        print(f"✅ Saytga yuklandi: {title}")
    else:
        print(f"❌ GitHub xatolik!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Oddiy xabarlar uchun (test)
    if update.message and update.message.text == "/start":
        await update.message.reply_text("🤍 Madridista Central Bot ishlayapti!")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN topilmadi!")
        return

    print(f"Bot ishga tushmoqda... Kanal: {CHANNEL_ID}")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Kanal postlarini tinglash
    app.add_handler(MessageHandler(
        filters.UpdateType.CHANNEL_POST,
        handle_channel_post
    ))

    # Oddiy xabarlar
    app.add_handler(MessageHandler(
        filters.TEXT & filters.PRIVATE,
        handle_message
    ))

    print("✅ Bot tayyor — postlarni kutmoqda...")
    app.run_polling(allowed_updates=["message", "channel_post"])

if __name__ == "__main__":
    main()
