import telebot
from telebot import types
import sqlite3

import os

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [os.getenv("ADMIN_ID"), os.getenv("ADMIN_ID_2")]  # Список ID админов
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
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}"
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        bot.reply_to(message, "Вы уже проходили анкету. Спасибо!")
    else:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
        conn.commit()
        send_intro(message)

# Отправка вступительного сообщения
def assigned_admin = ADMIN_IDS[len(admin_clients) % len(ADMIN_IDS)]  # Равномерное распределение клиентов
admin_clients[message.from_user.id] = assigned_admin  # Привязка клиента к админу
send_intro(message)
    bot.send_message(message.chat.id, "Добрый день, меня зовут Давид👋 я владелец сети магазинов 'Дым'💨\nРад знакомству😊\n\nЯ создал этого бота, чтобы дать своим гостям самый лучший сервис и предложение😍\n\nВы хотите, чтобы мы стали лучше для вас?", reply_markup=generate_yes_no_keyboard())
    bot.register_next_step_handler(message, ask_survey_consent)

# Генерация клавиатуры Да/Нет
def generate_yes_no_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет")
    return markup

# Спрашиваем, готов ли пользователь помочь
def ask_survey_consent(message):
    bot.send_message(message.chat.id, "Отлично✨\nТут я буду публиковать интересные предложения, розыгрыши и подарки 🎁\n\nНо самое главное, мы хотим улучшить качество нашей работы.\n\nСможете нам помочь, ответив на 3 вопроса?", reply_markup=generate_yes_no_keyboard())
    bot.register_next_step_handler(message, ask_likes)

# Вопрос о том, что ценят больше всего
def ask_likes(message):
    bot.send_message(message.chat.id, "Благодарим за помощь🤝\nПодскажите, какие 2 вещи в наших магазинах вы цените больше всего?")
    bot.register_next_step_handler(message, save_likes)

# Сохранение ответа о ценностях
def save_likes(message):
    cursor.execute("UPDATE users SET likes = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_dislikes(message)

# Вопрос о том, что не нравится
def ask_dislikes(message):
    bot.send_message(message.chat.id, "Хорошо😊\nИ еще пару вещей, которые вам больше всего не нравятся?")
    bot.register_next_step_handler(message, save_dislikes)

# Сохранение ответа о недостатках
def save_dislikes(message):
    cursor.execute("UPDATE users SET dislikes = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_suggestions(message)

# Вопрос о предложениях по улучшению
def ask_suggestions(message):
    bot.send_message(message.chat.id, "Отлично и последний вопрос)\nЧто бы вы изменили, будучи на моем месте, чтобы стать лучше?")
    bot.register_next_step_handler(message, save_suggestions)

# Сохранение предложений
def save_suggestions(message):
    cursor.execute("UPDATE users SET suggestions = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    ask_additional_info(message)

# Дополнительные вопросы (пол, возраст, частота посещений)
def ask_additional_info(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Мужской", "Женский")
    bot.send_message(message.chat.id, "Спасибо огромное за помощь😊\nЯ учту ваши пожелания и постараюсь приложить усилия, чтобы это исправить.\nЕсли не сложно, подскажите ваш пол:", reply_markup=markup)
    bot.register_next_step_handler(message, save_gender)

def save_gender(message):
    cursor.execute("UPDATE users SET gender = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("До 22", "22-30", "Более 30")
    bot.send_message(message.chat.id, "Укажите ваш возраст:", reply_markup=markup)
    bot.register_next_step_handler(message, save_age_group)

def save_age_group(message):
    cursor.execute("UPDATE users SET age_group = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Был до 3х раз", "3-8", "Более 8 раз")
    bot.send_message(message.chat.id, "Как часто вы нас посещали?", reply_markup=markup)
    bot.register_next_step_handler(message, save_visit_frequency)

def save_visit_frequency(message):
    cursor.execute("UPDATE users SET visit_frequency = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    
    # Отправляем анкету админу
    send_survey_to_admin(message.from_user.id)

    bot.send_message(message.chat.id, "Благодарю!\n📞 8-918-5567-53-33\nВот мой номер телефона, по нему вы всегда можете позвонить или написать в WhatsApp/Telegram.\n\nЕсли вам нужна информация о наличии, ценах или вкусах, напишите в наш чат: https://t.me/+BR14rdoGA91mZjdi")

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

# Пересылаем сообщения клиента назначенному админу
@bot.message_handler(func=lambda message: message.chat.id not in ADMIN_IDS)
def forward_to_admin(message):
    admin_id = admin_clients.get(message.from_user.id, ADMIN_IDS[0])  # Если нет привязки, отправляем первому админу
    bot.send_message(admin_id, f"Сообщение от {message.from_user.first_name}:\n\n{message.text}")

# Позволяем админу отвечать клиенту
@bot.message_handler(func=lambda message: message.chat.id in ADMIN_IDS and message.reply_to_message)
def reply_to_client(message):
    text = message.text
    client_id = int(message.reply_to_message.text.split("\n")[0].split(" ")[-1])  # Парсим ID клиента из пересланного сообщения

    if client_id:
        bot.send_message(client_id, f"Ответ от администратора:\n\n{text}")
        bot.send_message(message.chat.id, "Ответ отправлен клиенту.")
    else:
        bot.send_message(message.chat.id, "Ошибка: Не удалось определить ID клиента.")

# Запуск бота
bot.polling(non_stop=True)
