
import telebot
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import base64

# Токены
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

bot = telebot.TeleBot(BOT_TOKEN)
user_contexts = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я — *Инерция*, твой личный редактор. Пришли ссылку на канал или фото афиши — я всё прочитаю и помогу сделать текст в твоём стиле.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: 'https://t.me/' in msg.text)
def handle_channel_link(message):
    url = message.text.replace("https://t.me/", "https://t.me/s/")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all(class_='tgme_widget_message_text')
        extracted = [post.get_text(strip=True) for post in posts[:30]]

        if not extracted:
            bot.send_message(message.chat.id, "Не удалось получить посты. Возможно, канал закрыт.")
            return

        user_contexts[message.chat.id] = {"posts": extracted}

        prompt = (
            "Проанализируй 30 постов Telegram-канала по следующим 15 характеристикам и верни их в JSON:
"
            "1. Интонация
2. Обращение к читателю
3. Средняя длина поста
4. Приветствие
5. Подпись
"
            "6. Обороты
7. Юмор
8. Форматирование
9. Структура
10. Эмодзи
11. Тематика
"
            "12. Тональность
13. Художественные приёмы
14. Подача мнения
15. Ритм

"
            "Вот посты:
" + "\n\n".join(extracted)
        )

        bot.send_message(message.chat.id, "Анализирую канал...")

        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты анализируешь стиль Telegram-канала по 15 критериям и возвращаешь результат в формате JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        analysis = result.choices[0].message.content
        user_contexts[message.chat.id]["style"] = analysis

        bot.send_message(
            message.chat.id,
            "Готово! Пришли тему для поста — и я напишу его в твоём стиле. Или скинь афишу, и я опишу её так, как будто это сделал ты.",
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при анализе: {str(e)}")

@bot.message_handler(func=lambda msg: msg.chat.id in user_contexts and msg.text)
def generate_post(message):
    theme = message.text
    context = user_contexts.get(message.chat.id)
    style = context.get("style")
    prompt = (
        f"Вот детальный анализ стиля автора по 15 пунктам:
{style}

"
        f"Создай Telegram-пост на тему: "{theme}" в этом стиле. Сохрани структуру, интонацию, длину, форматирование и ритм."
    )

    try:
        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты — Telegram-редактор. Пиши пост точно в стиле, указанном в анализе."},
                {"role": "user", "content": prompt}
            ]
        )

        post = result.choices[0].message.content
        bot.send_message(message.chat.id, post, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при генерации поста: {str(e)}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        encoded_image = base64.b64encode(downloaded).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{encoded_image}"

        style = user_contexts.get(message.chat.id, {}).get("style", "")
        prompt = (
            f"Вот стиль Telegram-канала:
{style}

"
            "Посмотри на афишу и опиши её так, как сделал бы автор канала. Учитывай стиль, тональность, подачу, оформление. "
            "Если на афише есть текст — процитируй его. Итог — как будто это начало поста в стиле автора."
        )

        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        )

        description = result.choices[0].message.content
        bot.send_message(message.chat.id, description)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при обработке изображения: {str(e)}")

bot.infinity_polling()
