import telebot
import requests
from bs4 import BeautifulSoup
import openai
import base64
import os

# Токены
TELEGRAM_TOKEN = "8093617227:AAFqJV9Kqd4XmcmCX_qgiNo-gnmgR-W575Y"
OPENAI_API_KEY = "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"

openai.api_key = OPENAI_API_KEY
bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_contexts = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я Инерция — ИИ-агент для анализа Telegram-каналов и генерации постов в твоем стиле. Пришли мне ссылку на свой канал.")

@bot.message_handler(func=lambda msg: msg.text and 'https://t.me/' in msg.text)
def handle_channel_link(message):
    try:
        url = message.text.replace("https://t.me/", "https://t.me/s/")
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        posts = soup.find_all(class_="tgme_widget_message_text")
        extracted = [post.get_text(strip=True) for post in posts[:30]]
        if not extracted:
            bot.reply_to(message, "Не удалось получить посты. Канал может быть закрыт.")
            return
    except Exception as e:
        bot.reply_to(message, f"Ошибка при загрузке канала: {str(e)}")
        return

    try:
        joined = "\n\n".join(extracted)
        user_contexts[message.chat.id] = {"style": None, "posts": joined}

        prompt = (
            "Проанализируй посты Telegram-канала по следующим 15 характеристикам и верни их в JSON:\n"
            "1. Длина постов\n2. Форматирование (абзацы, списки, выделения)\n3. Использование эмодзи\n"
            "4. Юмор (тип, частота)\n5. Сарказм\n6. Интонация\n7. Повторяющиеся речевые обороты\n"
            "8. Приветствие\n9. Подпись\n10. Обращение к читателю\n11. Тематика\n12. Визуальные образы\n"
            "13. Цитаты\n14. Длина абзацев\n15. Уникальные стилистические приёмы"
        )

        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты профессиональный редактор и стилист Telegram-каналов."},
                {"role": "user", "content": prompt + "\n\n" + joined}
            ]
        )

        user_contexts[message.chat.id]["style"] = completion.choices[0].message.content

        bot.reply_to(message, "Спасибо! Я изучил последние 30 постов. Мне нравится твой стилёк, попробую продолжить в этом духе. Напиши тему — и я создам пост.")

    except Exception as e:
        bot.reply_to(message, f"Ошибка при анализе: {str(e)}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        image_b64 = base64.b64encode(downloaded).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{image_b64}"

        style = user_contexts.get(message.chat.id, {}).get("style", "")

        prompt = (
            f"Вот стиль Telegram-канала:\n{style}\n\n"
            "Посмотри на афишу и опиши её так, как сделал бы автор канала. Учитывай стиль, подачу, интонацию. "
            "Если есть текст — процитируй. Итог должен быть как начало поста в его стиле."
        )

        result = openai.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=500
        )

        bot.reply_to(message, result.choices[0].message.content)

    except Exception as e:
        bot.reply_to(message, f"Ошибка при анализе афиши: {str(e)}")

@bot.message_handler(func=lambda msg: True)
def generate_post(message):
    try:
        context = user_contexts.get(message.chat.id)
        if not context or not context.get("style"):
            bot.reply_to(message, "Сначала пришли ссылку на канал для анализа.")
            return

        prompt = (
            f"Вот стилистика автора:\n{context['style']}\n\n"
            f"Создай Telegram-пост в этом стиле. Тема: {message.text}. Сохрани структуру, приветствие, подачу, "
            f"обращения, юмор, если есть. Не используй эмодзи, если автор их не использует. Один вариант."
        )

        result = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты — Инерция, AI-копирайтер, создающий посты в заданной стилистике."},
                {"role": "user", "content": prompt}
            ]
        )

        bot.reply_to(message, result.choices[0].message.content)

    except Exception as e:
        bot.reply_to(message, f"Ошибка при генерации поста: {str(e)}")

bot.infinity_polling()
