import telebot
import requests
from bs4 import BeautifulSoup
import base64
import os
from openai import OpenAI

# Токены
TELEGRAM_TOKEN = "8093617227:AAFqJV9Kqd4XmcmCX_qgiNo-gnmgR-W575Y"
OPENAI_API_KEY = "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"

openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_contexts = {}

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я Инерция — ИИ-агент для анализа Telegram-каналов и помощи авторам. Пришли мне ссылку на свой канал.")

# Обработка ссылки на канал
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

        user_contexts[message.chat.id] = extracted

        bot.reply_to(message, "Спасибо! Я изучил последние посты. Мне нравится твой стилек. Попробую написать пост в таком духе. Пришли тему или идею.")

    except Exception as e:
        bot.reply_to(message, f"Ошибка при анализе: {str(e)}")

# Обработка ввода темы для генерации поста
@bot.message_handler(func=lambda msg: msg.chat.id in user_contexts)
def generate_post(message):
    posts = user_contexts[message.chat.id]
    prompt = (
        "Проанализируй стиль Telegram-канала на основе следующих постов:\n\n"
        + "\n---\n".join(posts)
        + f"\n\nТеперь напиши новый пост в этом же стиле на тему: {message.text}. Учитывай длину, речевые обороты, наличие эмодзи, структуру текста, уровень юмора, подписи и приветствия. Генерируй только один пост."
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Ты контент-редактор, который умеет подражать стилю телеграм-каналов."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        result = response.choices[0].message.content.strip()
        bot.reply_to(message, result)

    except Exception as e:
        bot.reply_to(message, f"Ошибка при генерации поста: {str(e)}")

bot.infinity_polling()
