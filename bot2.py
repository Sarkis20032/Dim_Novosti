import telebot
from telebot import types
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [int(os.getenv("ADMIN_ID")), int(os.getenv("ADMIN_ID_2"))]  # Приведение ID к int
admin_clients = {}  # Словарь для привязки клиента к админу

bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных SQLite
conn = sqlite3.connect('clients.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    likes TEXT,
    dislikes TEXT,
    suggestions TEXT,
    gender TEXT,
    age_group TEXT,
    visit_frequency TEXT
)
""")
conn.commit()

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        bot.reply_to(message, "Вы уже проходили анкету. Спасибо!")
    else:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
        conn.commit()

        assigned_admin = ADMIN_IDS[len(admin_clients) % len(ADMIN_IDS)]
        admin_clients[user_id] = assigned_admin  

        bot.send_message(
            message.chat.id, 
            "Добрый день, меня зовут Давид👋 я владелец сети магазинов 'Дым'💨\n"
            "Рад знакомству😊\n\n"
            "Я создал этого бота, чтобы дать своим гостям самый лучший сервис и предложение😍\n\n"
            "Вы хотите, чтобы мы стали лучше для вас?",
            reply_markup=generate_yes_no_keyboard()
        )
        bot.register_next_step_handler(message, ask_survey_consent)

# Генерация клавиатуры Да/Нет
def generate_yes_no_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    return markup

# Вопрос об участии в опросе
def ask_survey_consent(message):
    bot.send_message(
        message.chat.id, 
        "Отлично✨\nТут я буду публиковать интересные предложения, розыгрыши и подарки 🎁\n\n"
        "Но самое главное, мы хотим улучшить качество нашей работы.\n\n"
        "Сможете нам помочь, ответив на 3 вопроса?", 
        reply_markup=generate_yes_no_keyboard()
    )
    bot.register_next_step_handler(message, ask_likes)

# Вопрос о том, что ценят больше всего
def ask_likes(message):
    bot.send_message(message.chat.id, "Благодарим за помощь🤝\nПодскажите, какие 2 вещи в наших магазинах вы цените больше всего?")
    bot.register_next_step_handler(message, save_likes)

# Сохранение ответа
def save_likes(message):
    cursor.execute("UPDATE users SET likes = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_dislikes(message)

def ask_dislikes(message):
    bot.send_message(message.chat.id, "Хорошо😊\nИ еще пару вещей, которые вам больше всего не нравятся?")
    bot.register_next_step_handler(message, save_dislikes)

def save_dislikes(message):
    cursor.execute("UPDATE users SET dislikes = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_suggestions(message)

def ask_suggestions(message):
    bot.send_message(message.chat.id, "Что бы вы изменили, будучи на моем месте, чтобы стать лучше?")
    bot.register_next_step_handler(message, save_suggestions)

def save_suggestions(message):
    cursor.execute("UPDATE users SET suggestions = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_gender(message)

# Вопрос о поле пользователя
def ask_gender(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Мужской", "Женский")
    bot.send_message(message.chat.id, "Какой у вас пол?", reply_markup=markup)
    bot.register_next_step_handler(message, save_gender)

def save_gender(message):
    cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_age_group(message)

def ask_age_group(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("18-25", "26-35", "36-45", "46+")
    bot.send_message(message.chat.id, "Выберите вашу возрастную группу:", reply_markup=markup)
    bot.register_next_step_handler(message, save_age_group)

def save_age_group(message):
    cursor.execute("UPDATE users SET age_group = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_visit_frequency(message)

def ask_visit_frequency(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Раз в неделю", "Раз в месяц", "Раз в полгода", "Редко")
    bot.send_message(message.chat.id, "Как часто вы посещаете наши магазины?", reply_markup=markup)
    bot.register_next_step_handler(message, save_visit_frequency)

def save_visit_frequency(message):
    cursor.execute("UPDATE users SET visit_frequency = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    bot.send_message(message.chat.id, "Спасибо за участие в опросе! 😊")
    send_survey_to_admin(message.from_user.id)

@bot.message_handler(commands=['count_clients'])
def count_clients(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    bot.reply_to(message, f"Количество клиентов в базе: {count}")

bot.polling(non_stop=True)
