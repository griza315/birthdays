FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода бота
COPY birthday_bot.py .

# Переменные окружения (необходимо установить при запуске)
ENV TELEGRAM_TOKEN=""
ENV CHAT_ID=""
ENV DB_PATH="/app/birthdays.db"

# Создание тома для сохранения базы данных
VOLUME ["/app"]

# Запуск бота
CMD ["python", "birthday_bot.py"]
