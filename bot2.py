import telebot
from telebot import types
import sqlite3
import os
import threading
import time

# Загрузка переменных окружения
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise ValueError("TOKEN не задан!")
if not ADMIN_ID or not ADMIN_ID.isdigit():
    raise ValueError("ADMIN_ID не задан или неверен!")

ADMIN_ID = int(ADMIN_ID)
ADMIN_IDS = {ADMIN_ID}

bot = telebot.TeleBot(TOKEN)

# Блокировка для безопасного доступа к БД
db_lock = threading.Lock()

# Подключение к базе данных
conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

# Функция безопасного выполнения SQL-запросов
def safe_execute(query, params=()):
    with db_lock:
        cursor.execute(query, params)
        conn.commit()

# Создание таблиц
safe_execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    likes TEXT,
    dislikes TEXT,
    suggestions TEXT,
    gender TEXT,
    age_group TEXT,
    visit_frequency TEXT,
    survey_completed INTEGER DEFAULT 0
)
""")

safe_execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
""")

# Команда для добавления администратора
@bot.message_handler(commands=['add_admin'])
def add_admin(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return
    bot.reply_to(message, "Введите ID нового администратора:")
    bot.register_next_step_handler(message, save_admin)

def save_admin(message):
    try:
        new_admin_id = int(message.text)
        ADMIN_IDS.add(new_admin_id)
        bot.reply_to(message, f"Администратор {new_admin_id} добавлен!")
    except ValueError:
        bot.reply_to(message, "Ошибка! Введите корректный ID.")

# Команда для переписки с клиентами
@bot.message_handler(commands=['message'])
def select_client(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "У вас нет прав.")
        return
    bot.reply_to(message, "Введите ID клиента, которому хотите написать:")
    bot.register_next_step_handler(message, send_message_to_client)

def send_message_to_client(message):
    try:
        user_id = int(message.text.strip())
        bot.reply_to(message, "Введите сообщение клиенту:")
        bot.register_next_step_handler(message, lambda msg: forward_message_to_client(msg, user_id))
    except ValueError:
        bot.reply_to(message, "Ошибка! Введите корректный ID.")

def forward_message_to_client(message, user_id):
    try:
        bot.send_message(user_id, message.text)
        bot.reply_to(message, "Сообщение отправлено!")
    except Exception as e:
        bot.reply_to(message, f"Ошибка отправки: {e}")

# Запоминаем входящие сообщения (только если клиент прошёл анкету)
@bot.message_handler(func=lambda message: True)
def check_survey(message):
    user_id = message.from_user.id
    cursor.execute("SELECT survey_completed FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result and result[0] == 1:
        bot.send_message(message.chat.id, "Вы прошли анкетирование! Можете пользоваться ботом.")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите анкетирование! Напишите /start.")

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}"

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        bot.reply_to(message, "Вы уже проходили анкету. Спасибо!")
    else:
        safe_execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
        send_intro(message)

# Отправка вступительного сообщения
def send_intro(message):
    bot.send_message(message.chat.id, "Добрый день, меня зовут Давид👋 ...\nВы хотите, чтобы мы стали лучше для вас?", reply_markup=generate_yes_no_keyboard())
    bot.register_next_step_handler(message, ask_survey_consent)

def generate_yes_no_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    return markup

# Анкетирование
def ask_survey_consent(message):
    bot.send_message(message.chat.id, "Отлично!...\nСможете нам помочь, ответив на 3 вопроса?", reply_markup=generate_yes_no_keyboard())
    bot.register_next_step_handler(message, ask_likes)

def ask_likes(message):
    bot.send_message(message.chat.id, "Какие 2 вещи в наших магазинах вы цените больше всего?")
    bot.register_next_step_handler(message, save_likes)

def save_likes(message):
    safe_execute("UPDATE users SET likes = ? WHERE user_id = ?", (message.text, message.from_user.id))
    ask_dislikes(message)

def ask_dislikes(message):
    bot.send_message(message.chat.id, "Какие вещи вам не нравятся?")
    bot.register_next_step_handler(message, save_dislikes)

def save_dislikes(message):
    safe_execute("UPDATE users SET dislikes = ? WHERE user_id = ?", (message.text, message.from_user.id))
    ask_suggestions(message)

def ask_suggestions(message):
    bot.send_message(message.chat.id, "Что бы вы изменили, будучи на моем месте?")
    bot.register_next_step_handler(message, save_suggestions)

def save_suggestions(message):
    safe_execute("UPDATE users SET suggestions = ?, survey_completed = 1 WHERE user_id = ?", (message.text, message.from_user.id))
    bot.send_message(message.chat.id, "Спасибо за анкету! Теперь вы можете писать нам сообщения.")

# Команда очистки базы
@bot.message_handler(commands=['clear_database'])
def clear_database(message):
    if message.from_user.id in ADMIN_IDS:
        safe_execute("DELETE FROM users")
        bot.reply_to(message, "База данных успешно очищена.")
    else:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")

# Команда просмотра базы
@bot.message_handler(commands=['count_clients'])
def count_clients(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    bot.reply_to(message, f"Количество зарегистрированных клиентов: {count}")

# Команда для рассылки
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "У вас нет прав.")
        return
    bot.reply_to(message, "Введите текст для рассылки:")
    bot.register_next_step_handler(message, perform_broadcast)

def perform_broadcast(message):
    cursor.execute("SELECT user_id FROM users")
    for user_id, in cursor.fetchall():
        try:
            bot.send_message(user_id, message.text)
        except:
            pass
    bot.reply_to(message, "Рассылка завершена.")

# Запуск бота с обработкой ошибок
while True:
    try:
        bot.polling(non_stop=True, skip_pending=True)
    except Exception as e:
        print(f"Ошибка в polling: {e}")
        time.sleep(5)  # Ожидание перед перезапуском
