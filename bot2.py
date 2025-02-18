import telebot
from telebot import types
import sqlite3
import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

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

# Храним прогресс пользователя
user_progress = {}

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
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
        conn.commit()
        send_intro(message)

# Вопрос о поле, возрасте и частоте посещений (одно сообщение)
def ask_additional_info(message):
    user_progress[message.from_user.id] = {"answers": []}  # Создаём запись в словаре

    bot.send_message(message.chat.id, 
                     "Спасибо огромное за помощь😊\nЯ учту ваши пожелания и постараюсь приложить усилия, чтобы это исправить.\n\n"
                     "Ответьте на три вопроса одним за другим:\n"
                     "1️⃣ Ваш пол (Мужской / Женский)\n"
                     "2️⃣ Ваш возраст (До 22 / 22-30 / Более 30)\n"
                     "3️⃣ Как часто посещали наш магазин? (Был до 3х раз / 3-8 / Более 8 раз)")
    
    bot.register_next_step_handler(message, collect_three_answers)

# Получаем три последовательных ответа
def collect_three_answers(message):
    user_id = message.from_user.id
    
    if user_id not in user_progress:
        user_progress[user_id] = {"answers": []}
    
    user_progress[user_id]["answers"].append(message.text)  # Добавляем ответ в список
    
    if len(user_progress[user_id]["answers"]) < 3:
        bot.register_next_step_handler(message, collect_three_answers)  # Ждём следующий ответ
    else:
        save_additional_info(message)

# Сохранение ответов в БД
def save_additional_info(message):
    user_id = message.from_user.id
    answers = user_progress.get(user_id, {}).get("answers", [])
    
    if len(answers) == 3:
        gender, age_group, visit_frequency = answers
        cursor.execute("UPDATE users SET gender = ?, age_group = ?, visit_frequency = ? WHERE user_id = ?",
                       (gender, age_group, visit_frequency, user_id))
        conn.commit()
        send_survey_to_admin(user_id)
        bot.send_message(message.chat.id, "Благодарю!\n📞 8-918-5567-53-33\nВот мой номер телефона, по нему вы всегда можете позвонить или написать в WhatsApp/Telegram.\n\n"
                                          "Если вам нужна информация о наличии, ценах или вкусах, напишите в наш чат: https://t.me/+BR14rdoGA91mZjdi")
    
    user_progress.pop(user_id, None)  # Удаляем данные после обработки

# Отправка анкеты админу
def send_survey_to_admin(user_id):
    cursor.execute("SELECT full_name, likes, dislikes, suggestions, gender, age_group, visit_frequency FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    if user_data:
        full_name, likes, dislikes, suggestions, gender, age_group, visit_frequency = user_data
        survey_text = f"Новая анкета клиента:\n\n"
        survey_text += f"Имя: {full_name}\n"
        survey_text += f"Ценит: {likes}\n"
        survey_text += f"Не нравится: {dislikes}\n"
        survey_text += f"Предложения: {suggestions}\n"
        survey_text += f"Пол: {gender}\n"
        survey_text += f"Возраст: {age_group}\n"
        survey_text += f"Частота посещений: {visit_frequency}\n"
        
        bot.send_message(ADMIN_ID, survey_text)

# Команда для очистки базы
@bot.message_handler(commands=['clear_database'])
def clear_database(message):
    cursor.execute("DELETE FROM users")
    conn.commit()
    bot.reply_to(message, "База данных успешно очищена.")

# Команда для просмотра базы
@bot.message_handler(commands=['count_clients'])
def count_clients(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    bot.reply_to(message, f"Количество зарегистрированных клиентов: {count}")

# Команда для рассылки
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.from_user.id) != ADMIN_ID:
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
