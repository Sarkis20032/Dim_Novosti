import telebot
from telebot import types
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [int(os.getenv("ADMIN_ID")), int(os.getenv("ADMIN_ID_2"))]  # Приводим ID к int
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

        # Равномерное распределение клиентов между администраторами
        assigned_admin = ADMIN_IDS[len(admin_clients) % len(ADMIN_IDS)]
        admin_clients[user_id] = assigned_admin  # Привязываем клиента к админу

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
    ask_additional_info(message)

# Отправка анкеты админу
def send_survey_to_admin(user_id):
    cursor.execute("SELECT full_name, likes, dislikes, suggestions, gender, age_group, visit_frequency FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    if user_data:
        full_name, likes, dislikes, suggestions, gender, age_group, visit_frequency = user_data
        survey_text = (
            f"📋 Новая анкета клиента:\n\n"
            f"👤 Имя: {full_name}\n"
            f"✅ Ценит: {likes}\n"
            f"❌ Не нравится: {dislikes}\n"
            f"💡 Предложения: {suggestions}\n"
            f"🧑‍🤝‍🧑 Пол: {gender}\n"
            f"📅 Возраст: {age_group}\n"
            f"📍 Частота посещений: {visit_frequency}"
        )
        
        admin_id = admin_clients.get(user_id, ADMIN_IDS[0])  # Назначенный админ
        bot.send_message(admin_id, survey_text)

# Команда для очистки базы
@bot.message_handler(commands=['clear_database'])
def clear_database(message):
    cursor.execute("DELETE FROM users")
    conn.commit()
    bot.reply_to(message, "База данных успешно очищена.")

# Команда для рассылки
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return
    bot.reply_to(message, "Введите текст для рассылки:")
    bot.register_next_step_handler(message, perform_broadcast)

def perform_broadcast(message):
    cursor.execute("SELECT user_id FROM users")
    user_ids = cursor.fetchall()
    for user_id in user_ids:
        try:
            bot.send_message(user_id[0], message.text)
        except:
            pass
    bot.reply_to(message, "Рассылка завершена.")

# Запуск бота
bot.polling(non_stop=True)
