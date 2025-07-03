import telebot
import sqlite3
import os
import time
import logging
from dotenv import load_dotenv


# Загружаем переменные из .env файла (если он есть)
load_dotenv()

# Получаем токен из переменной окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Необходимо установить переменную окружения BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

busy = False
user = {
    'id': '',
    'first_name': '',
    'last_name': '',
    'username': ''
}

# Database setup
DB_NAME = os.environ.get('DB_PATH')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 31653534)) # с значением по умолчанию
ADMIN_USERNAME = 'BrotherCash'
ADMIN_NAME = 'Игорь Владимирович'


def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY,
                       tg_id
                       INTEGER
                       UNIQUE,
                       username
                       TEXT,
                       first_name
                       TEXT,
                       last_name
                       TEXT,
                       role
                       TEXT
                       DEFAULT
                       'user',
                       status
                       TEXT
                       DEFAULT
                       'pending',
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')

    # Add default admin if not exists
    cursor.execute('''
                   INSERT
                   OR IGNORE INTO users (tg_id, username, first_name, role, status) 
        VALUES (?, ?, ?, 'admin', 'approved')
                   ''', (ADMIN_ID, ADMIN_USERNAME, ADMIN_NAME))

    conn.commit()
    conn.close()


def get_user_status(tg_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT role, status FROM users WHERE tg_id = ?', (tg_id,))
    result = cursor.fetchone()

    conn.close()
    return result


def add_user(tg_id, username, first_name, last_name, status='pending'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO users (tg_id, username, first_name, last_name, status) 
        VALUES (?, ?, ?, ?, ?)
    ''', (tg_id, username, first_name, last_name, status))

    conn.commit()
    conn.close()


def update_user_status(tg_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('UPDATE users SET status = ? WHERE tg_id = ?', (status, tg_id))

    conn.commit()
    conn.close()


def is_authorized(tg_id):
    user_data = get_user_status(tg_id)
    return user_data is not None and user_data[1] == 'approved'


def is_admin(tg_id):
    user_data = get_user_status(tg_id)
    return user_data is not None and user_data[0] == 'admin'


def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tg_id, username, first_name, last_name, role, status, created_at 
        FROM users 
        ORDER BY created_at DESC
    ''')
    results = cursor.fetchall()
    
    conn.close()
    return results


# Initialize database
init_database()

# Create keyboards
keyboard1 = telebot.types.ReplyKeyboardMarkup(True)
keyboard1.row('BS ON', 'BS OFF')

admin_keyboard = telebot.types.ReplyKeyboardMarkup(True)
admin_keyboard.row('BS ON', 'BS OFF')
admin_keyboard.row('👥 Пользователи')


@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id

    # Check if user is already authorized
    if is_authorized(user_id):
        keyboard = admin_keyboard if is_admin(user_id) else keyboard1
        bot.send_message(message.chat.id, 'Бот запущен', reply_markup=keyboard)
        return

    # Check if user already exists in database
    user_data = get_user_status(user_id)
    if user_data is not None:
        if user_data[1] == 'blocked':
            bot.send_message(message.chat.id, 'Доступ заблокирован администратором.')
            return
        elif user_data[1] == 'pending':
            bot.send_message(message.chat.id,
                             'Ваш запрос на авторизацию уже отправлен администратору. Ожидайте одобрения.')
            return

    # New user - add to database and request authorization
    username = message.from_user.username or ''
    first_name = message.from_user.first_name or ''
    last_name = message.from_user.last_name or ''

    add_user(user_id, username, first_name, last_name, 'pending')

    # Send authorization request to admin
    auth_keyboard = telebot.types.InlineKeyboardMarkup()
    auth_keyboard.add(
        telebot.types.InlineKeyboardButton('Да', callback_data=f'approve_{user_id}'),
        telebot.types.InlineKeyboardButton('Нет', callback_data=f'reject_{user_id}')
    )

    user_info = f'{first_name} {last_name}'.strip()
    username_text = f'@{username}' if username else 'без username'

    bot.send_message(
        ADMIN_ID,
        f'Пользователь {user_info} ({username_text}) просит авторизации.\nАвторизовать?',
        reply_markup=auth_keyboard
    )

    bot.send_message(message.chat.id, 'Запрос на авторизацию отправлен администратору. Ожидайте одобрения.')


@bot.message_handler(content_types=['text'])
def send_text(message):
    global busy
    global user

    # Check authorization first
    if not is_authorized(message.from_user.id):
        bot.send_message(message.chat.id, 'Вы не авторизованы. Выполните команду /start для авторизации')
        return

    print(message)
    
    # Admin commands
    if message.text == '👥 Пользователи' and is_admin(message.from_user.id):
        users = get_all_users()
        if not users:
            bot.send_message(message.chat.id, 'Пользователей нет в базе данных.')
            return
            
        text = '👥 *Список пользователей:*\n\n'
        for user_data in users:
            tg_id, username, first_name, last_name, role, status, created_at = user_data
            
            name = f'{first_name or ""} {last_name or ""}'.strip()
            username_text = f'@{username}' if username else 'без username'
            
            status_emoji = {
                'approved': '✅',
                'pending': '⏳',
                'blocked': '❌'
            }.get(status, '❓')
            
            role_emoji = '👑' if role == 'admin' else '👤'
            
            text += f'{role_emoji} *{name}* ({username_text})\n'
            text += f'ID: `{tg_id}` | Статус: {status_emoji} {status}\n\n'
        
        # Create inline keyboard for user management
        keyboard = telebot.types.InlineKeyboardMarkup()
        
        # Add buttons for each user (except current admin)
        for user_data in users:
            tg_id, username, first_name, last_name, role, status, created_at = user_data
            if tg_id == message.from_user.id:  # Skip current admin
                continue
                
            name = f'{first_name or ""} {last_name or ""}'.strip() or username or str(tg_id)
            keyboard.add(telebot.types.InlineKeyboardButton(
                f'⚙️ Управлять: {name}', 
                callback_data=f'manage_user_{tg_id}'
            ))
        
        keyboard.add(telebot.types.InlineKeyboardButton('🔄 Обновить список', callback_data='refresh_users'))
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=keyboard)
        return

    if message.text == 'BS ON' and busy is not True:

        user['id'] = message.from_user.id
        if message.from_user.first_name is not None:
            user['first_name'] = message.from_user.first_name
        else:
            user['first_name'] = ''

        if message.from_user.last_name is not None:
            user['last_name'] = message.from_user.last_name
        else:
            user['last_name'] = ''

        if message.from_user.username is not None:
            user['username'] = '(@' + message.from_user.username + ')'
        else:
            user['username'] = ''

        bot.send_message(message.chat.id,
                         f"""Работа с BrowserStack НАЧАТА.
Пользователь - {user['first_name']} {user['last_name']} {user['username']}"""
                         )
        busy = True

    elif message.text == 'BS ON' and busy is True:

        bot.send_message(message.chat.id,
                         f"""Вы не можете воспользоваться сервисом BrowserStack. 
В даный момент он используется пользователем 
{user['first_name']} {user['last_name']} {user['username']} """
                         )

    elif message.text == 'BS OFF' and busy is not True:
        bot.send_message(message.chat.id,
                         f"""Сервис BrowserStack в данный момент свободен."""
                         )

    elif message.text == 'BS OFF':
        if message.from_user.id == user['id']:
            bot.send_message(message.chat.id,
                             f"""Работа с BrowserStack ЗАКОНЧЕНА.
Пользователь - {user['first_name']} {user['last_name']} {user['username']}"""
                             )
            busy = False
        else:
            bot.send_message(message.chat.id,
                             f"""Вы не можете завершить работу
с сервисом BrowserStack.
В данный момент он используется пользователем 
{user['first_name']} {user['last_name']} {user['username']} """
                             )


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, 'У вас нет прав администратора')
        return

    # Handle refresh users list
    if call.data == 'refresh_users':
        users = get_all_users()
        if not users:
            bot.edit_message_text('Пользователей нет в базе данных.', call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, 'Список обновлен')
            return
            
        text = '👥 *Список пользователей:*\n\n'
        for user_data in users:
            tg_id, username, first_name, last_name, role, status, created_at = user_data
            
            name = f'{first_name or ""} {last_name or ""}'.strip()
            username_text = f'@{username}' if username else 'без username'
            
            status_emoji = {
                'approved': '✅',
                'pending': '⏳',
                'blocked': '❌'
            }.get(status, '❓')
            
            role_emoji = '👑' if role == 'admin' else '👤'
            
            text += f'{role_emoji} *{name}* ({username_text})\n'
            text += f'ID: `{tg_id}` | Статус: {status_emoji} {status}\n\n'
        
        # Create inline keyboard for user management
        keyboard = telebot.types.InlineKeyboardMarkup()
        
        # Add buttons for each user (except current admin)
        for user_data in users:
            tg_id, username, first_name, last_name, role, status, created_at = user_data
            if tg_id == call.from_user.id:  # Skip current admin
                continue
                
            name = f'{first_name or ""} {last_name or ""}'.strip() or username or str(tg_id)
            keyboard.add(telebot.types.InlineKeyboardButton(
                f'⚙️ Управлять: {name}', 
                callback_data=f'manage_user_{tg_id}'
            ))
        
        keyboard.add(telebot.types.InlineKeyboardButton('🔄 Обновить список', callback_data='refresh_users'))
        
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            if "message is not modified" not in str(e):
                raise e
        bot.answer_callback_query(call.id, 'Список обновлен')
        return

    # Handle user management
    if call.data.startswith('manage_user_'):
        user_id = int(call.data.split('_')[2])
        user_data = get_user_status(user_id)
        
        if not user_data:
            bot.answer_callback_query(call.id, 'Пользователь не найден')
            return
            
        # Get full user info
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT tg_id, username, first_name, last_name, role, status FROM users WHERE tg_id = ?', (user_id,))
        user_info = cursor.fetchone()
        conn.close()
        
        if not user_info:
            bot.answer_callback_query(call.id, 'Пользователь не найден')
            return
            
        tg_id, username, first_name, last_name, role, status = user_info
        name = f'{first_name or ""} {last_name or ""}'.strip()
        username_text = f'@{username}' if username else 'без username'
        
        text = f'👤 *Управление пользователем*\n\n'
        text += f'Имя: {name}\n'
        text += f'Username: {username_text}\n'
        text += f'ID: `{tg_id}`\n'
        text += f'Статус: {status}\n'
        text += f'Роль: {role}'
        
        # Create status management keyboard
        keyboard = telebot.types.InlineKeyboardMarkup()
        
        if status != 'approved':
            keyboard.add(telebot.types.InlineKeyboardButton('✅ Одобрить', callback_data=f'set_status_{user_id}_approved'))
        if status != 'blocked':
            keyboard.add(telebot.types.InlineKeyboardButton('❌ Заблокировать', callback_data=f'set_status_{user_id}_blocked'))
        if status != 'pending':
            keyboard.add(telebot.types.InlineKeyboardButton('⏳ На рассмотрение', callback_data=f'set_status_{user_id}_pending'))
            
        keyboard.add(telebot.types.InlineKeyboardButton('🔙 Назад к списку', callback_data='refresh_users'))
        
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            if "message is not modified" not in str(e):
                raise e
        bot.answer_callback_query(call.id)
        return

    # Handle status changes
    if call.data.startswith('set_status_'):
        parts = call.data.split('_')
        user_id = int(parts[2])
        new_status = parts[3]
        
        # Update status
        update_user_status(user_id, new_status)
        
        # Notify user if status changed to approved
        if new_status == 'approved':
            try:
                keyboard = admin_keyboard if is_admin(user_id) else keyboard1
                bot.send_message(user_id, 'Ваш запрос на авторизацию одобрен! Теперь вы можете пользоваться ботом.',
                                reply_markup=keyboard)
            except:
                pass
        elif new_status == 'blocked':
            try:
                bot.send_message(user_id, 'Ваш доступ к боту заблокирован.')
            except:
                pass
        
        bot.answer_callback_query(call.id, f'Статус изменен на: {new_status}')
        
        # Refresh the user management view
        bot.callback_query_handler(func=lambda c: c.data == f'manage_user_{user_id}')(call)
        return

    # Handle legacy approval/rejection (for old authorization messages)
    if call.data.startswith('approve_') or call.data.startswith('reject_'):
        action, user_id = call.data.split('_')
        user_id = int(user_id)

        if action == 'approve':
            update_user_status(user_id, 'approved')
            bot.answer_callback_query(call.id, 'Пользователь авторизован')

            # Notify user about approval
            try:
                keyboard = admin_keyboard if is_admin(user_id) else keyboard1
                bot.send_message(user_id, 'Ваш запрос на авторизацию одобрен! Теперь вы можете пользоваться ботом.',
                                reply_markup=keyboard)
            except:
                pass

            # Update admin message
            bot.edit_message_text(
                '✅ Пользователь авторизован',
                call.message.chat.id,
                call.message.message_id
            )

        elif action == 'reject':
            update_user_status(user_id, 'blocked')
            bot.answer_callback_query(call.id, 'Пользователь заблокирован')

            # Notify user about rejection
            try:
                bot.send_message(user_id, 'Ваш запрос на авторизацию отклонен.')
            except:
                pass

            # Update admin message
            bot.edit_message_text(
                '❌ Пользователь заблокирован',
                call.message.chat.id,
                call.message.message_id
            )


def run_bot():
    """Запуск бота с обработкой сетевых ошибок и автоматическим переподключением"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    retry_count = 0
    max_retries = 5
    base_delay = 10
    
    while True:
        try:
            logging.info(f"Запуск бота (попытка {retry_count + 1})")
            bot.polling(none_stop=True, interval=1, timeout=20)
            
        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            
            if "Connection aborted" in error_msg or "Connection broken" in error_msg or \
               "Network is unreachable" in error_msg or "Read timed out" in error_msg or \
               "Connection reset" in error_msg or "Name or service not known" in error_msg:
                
                delay = min(base_delay * (2 ** min(retry_count - 1, 4)), 300)
                logging.warning(f"Сетевая ошибка: {error_msg}")
                logging.info(f"Переподключение через {delay} сек (попытка {retry_count}/{max_retries})")
                
                if retry_count >= max_retries:
                    logging.error(f"Превышено максимальное количество попыток ({max_retries}). Сброс счетчика.")
                    retry_count = 0
                    delay = 60
                
                time.sleep(delay)
                continue
            else:
                logging.error(f"Критическая ошибка: {error_msg}")
                raise


if __name__ == "__main__":
    run_bot()
