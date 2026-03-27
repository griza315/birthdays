#!/usr/bin/env python3
"""
Telegram бот для уведомления о днях рождения из SQLite базы данных.
Проверяет дни рождения ежедневно и отправляет уведомления:
- За 7 дней до дня рождения
- За 3 дня до дня рождения
- В сам день рождения
"""

import os
import sqlite3
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import telebot
from telebot import types

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
DB_PATH = os.getenv('DB_PATH', 'birthdays.db')

if not TELEGRAM_TOKEN:
    raise ValueError("Необходимо установить переменную окружения TELEGRAM_TOKEN")
if not CHAT_ID:
    raise ValueError("Необходимо установить переменную окружения CHAT_ID")

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Создание таблицы и подключение к БД
def init_db():
    """Инициализация базы данных и создание таблицы, если она не существует"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS birthdays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birth_date DATE NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"База данных инициализирована: {DB_PATH}")

def get_db_connection():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_birthdays():
    """Проверка дней рождения и отправка уведомлений"""
    try:
        today = datetime.now().date()
        logger.info(f"Проверка дней рождения на {today}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем все записи из таблицы
        cursor.execute('SELECT name, birth_date FROM birthdays')
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        
        for row in rows:
            name = row['name']
            birth_date_str = row['birth_date']
            
            # Парсим дату рождения (ожидается формат YYYY-MM-DD или DD.MM.YYYY)
            try:
                if '-' in birth_date_str:
                    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                elif '.' in birth_date_str:
                    birth_date = datetime.strptime(birth_date_str, '%d.%m.%Y').date()
                else:
                    logger.warning(f"Неизвестный формат даты для {name}: {birth_date_str}")
                    continue
            except ValueError as e:
                logger.error(f"Ошибка парсинга даты для {name}: {e}")
                continue
            
            # Создаем дату дня рождения в текущем году
            birthday_this_year = birth_date.replace(year=today.year)
            
            # Вычисляем разницу в днях
            if birthday_this_year >= today:
                days_until = (birthday_this_year - today).days
            else:
                # День рождения в этом году уже прошел, считаем до следующего года
                birthday_next_year = birth_date.replace(year=today.year + 1)
                days_until = (birthday_next_year - today).days
            
            # Проверяем условия для уведомлений
            if days_until == 0:
                messages.append(f"🎂 У {name} сегодня день рождения!")
            elif days_until == 3:
                messages.append(f"🎁 Через 3 дня у {name} день рождения!")
            elif days_until == 7:
                messages.append(f"🎉 Через 7 дней у {name} день рождения!")
        
        # Отправляем сообщения
        if messages:
            for message in messages:
                send_notification(message)
            logger.info(f"Отправлено {len(messages)} уведомлений")
        else:
            logger.info("Дней рождения для уведомления не найдено")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке дней рождения: {e}", exc_info=True)

def send_notification(message):
    """Отправка уведомления в Telegram"""
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        logger.info(f"Сообщение отправлено: {message}")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")

# Обработчики команд бота
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 Привет! Я бот для напоминания о днях рождения.\n\n"
        "Я проверяю дни рождения каждый день в 09:00 и отправляю уведомления:\n"
        "• За 7 дней до дня рождения 🎉\n"
        "• За 3 дня до дня рождения 🎁\n"
        "• В сам день рождения 🎂\n\n"
        "Доступные команды:\n"
        "/start - Показать это сообщение\n"
        "/check - Проверить дни рождения прямо сейчас\n"
        "/add <Имя> <Дата> - Добавить день рождения (дата в формате YYYY-MM-DD или DD.MM.YYYY)\n"
        "/list - Показать список всех дней рождения\n"
        "/delete <ID> - Удалить запись по ID\n"
        "/status - Показать статус бота"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['check'])
def manual_check(message):
    """Обработчик команды /check для ручной проверки"""
    bot.reply_to(message, "🔍 Выполняю проверку дней рождения...")
    check_birthdays()
    bot.reply_to(message, "✅ Проверка завершена!")

@bot.message_handler(commands=['add'])
def add_birthday(message):
    """Обработчик команды /add для добавления дня рождения"""
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Использование: /add <Имя> <Дата>\nПример: /add Иван 1990-05-15")
            return
        
        name = parts[1]
        date_str = parts[2]
        
        # Парсим дату
        try:
            if '-' in date_str:
                birth_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                db_format = birth_date.strftime('%Y-%m-%d')
            elif '.' in date_str:
                birth_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                db_format = birth_date.strftime('%Y-%m-%d')
            else:
                raise ValueError("Неизвестный формат даты")
        except ValueError:
            bot.reply_to(message, "❌ Неверный формат даты. Используйте YYYY-MM-DD или DD.MM.YYYY")
            return
        
        # Добавляем в базу данных
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO birthdays (name, birth_date) VALUES (?, ?)', (name, db_format))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        bot.reply_to(message, f"✅ Добавлен день рождения: {name} ({date_str})\nID записи: {record_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении дня рождения: {e}")
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['list'])
def list_birthdays(message):
    """Обработчик команды /list для показа всех дней рождения"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, birth_date FROM birthdays ORDER BY birth_date')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            bot.reply_to(message, "📭 Список дней рождения пуст")
            return
        
        response = "📅 Список дней рождения:\n\n"
        for row in rows:
            response += f"ID: {row['id']} | {row['name']} - {row['birth_date']}\n"
        
        bot.reply_to(message, response)
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка: {e}")
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['delete'])
def delete_birthday(message):
    """Обработчик команды /delete для удаления дня рождения"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Использование: /delete <ID>\nПример: /delete 1")
            return
        
        record_id = int(parts[1])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM birthdays WHERE id = ?', (record_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            bot.reply_to(message, f"✅ Запись с ID {record_id} удалена")
        else:
            bot.reply_to(message, f"❌ Запись с ID {record_id} не найдена")
        
        conn.close()
        
    except ValueError:
        bot.reply_to(message, "❌ ID должен быть числом")
    except Exception as e:
        logger.error(f"Ошибка при удалении: {e}")
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['status'])
def show_status(message):
    """Обработчик команды /status для показа статуса бота"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM birthdays')
        count = cursor.fetchone()[0]
        conn.close()
        
        status_text = (
            f"🤖 Статус бота:\n"
            f"• База данных: {DB_PATH}\n"
            f"• Всего записей: {count}\n"
            f"• Время проверки: ежедневно в 09:00\n"
            f"• Статус: ✅ Активен"
        )
        bot.reply_to(message, status_text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {e}")
        bot.reply_to(message, f"❌ Ошибка: {e}")

# Планировщик задач
scheduler = AsyncIOScheduler()

async def scheduled_check():
    """Асинхронная обертка для проверки дней рождения"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, check_birthdays)

def start_scheduler():
    """Запуск планировщика"""
    scheduler.add_job(
        scheduled_check,
        CronTrigger(hour=9, minute=0),
        id='daily_birthday_check',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Планировщик запущен. Проверка будет выполняться ежедневно в 09:00")

# Основной цикл бота
def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    init_db()
    
    # Запуск планировщика
    start_scheduler()
    
    logger.info("Бот запущен...")
    
    # Запуск бота в режиме polling
    bot.infinity_polling(skip_pending=True)

if __name__ == '__main__':
    main()
