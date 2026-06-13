import os
import json
import base64
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# === SOZLAMALAR ===
# Bu qiymatlarni .env faylga yozing, HECH QACHON bu yerga yozmang!
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")        # masalan: akbarking-jpg/MadridistaCentral
CHANNEL_ID = os.environ.get("CHANNEL_ID")           # masalan: @Madridista_Central

CATEGORIES = {
    "#transfer": "Transferlar",
    "#oyin": "O'yinlar",
    "#intervyu": "Intervyular",
    "#klub": "Klub yangiliklari",
    "#castilla": "Castilla",
    "#ayollar": "Ayollar jamoasi",
}

def detect_category(text):
    text_lower = text.lower()
    for tag, category in CATEGORIES.items():
        if tag in text_lower:
            return category
    return "Yangiliklar"

def get_news_json():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    return {"news": []}, None

def update_news_json(news_data, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/news.json"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    content = base64.b64encode(
        json.dumps(news_data, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": f"Yangi xabar qo'shildi: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content,
        "sha": sha
    }
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code == 200

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.message
    if not message or not message.text:
        return

    # Faqat kanaldan kelgan postlarni qayta ishlash
    chat = str(message.chat.username or message.chat.id)
    if CHANNEL_ID and f"@{chat}" != CHANNEL_ID and str(message.chat.id) != CHANNEL_ID:
        return

    text = message.text
    lines = text.strip().split("\n")
    title = lines[0][:100]  # Birinchi qator = sarlavha
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    category = detect_category(text)
    date = datetime.now().strftime("%Y-%m-%d")

    # news.json ni olish
    news_data, sha = get_news_json()
    if sha is None:
        print("GitHub'dan news.json olib bo'lmadi")
        return

    # Yangi ID
    new_id = max([n["id"] for n in news_data["news"]], default=0) + 1

    # Yangi yangilik qo'shish (eng boshiga)
    new_item = {
        "id": new_id,
        "title": title,
        "category": category,
        "date": date,
        "text": body,
        "image": ""
    }
    news_data["news"].insert(0, new_item)

    # Faqat so'nggi 50 ta yangilik
    news_data["news"] = news_data["news"][:50]

    # GitHub'ga yuklash
    if update_news_json(news_data, sha):
        print(f"✅ Yangilik saytga yuklandi: {title}")
    else:
        print(f"❌ GitHub'ga yuklashda xatolik")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(
        filters.TEXT & (filters.Chat() | filters.UpdateType.CHANNEL_POST),
        handle_message
    ))
    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
