# Telegram Birthday Bot - Docker

Этот проект упакован в Docker контейнер для удобного развертывания.

## Структура файлов

- `birthday_bot.py` - основной код бота
- `requirements.txt` - зависимости Python
- `Dockerfile` - конфигурация Docker образа
- `docker-compose.yml` - конфигурация для запуска через Docker Compose
- `.env.example` - пример файла с переменными окружения

## Подготовка

### 1. Получите токен бота и Chat ID

1. Создайте бота через [@BotFather](https://t.me/BotFather) в Telegram
2. Получите токен бота (TELEGRAM_TOKEN)
3. Добавьте бота в ваш чат/канал
4. Узнайте Chat ID (можно через бота @userinfobot или @getmyid_bot)

### 2. Создайте файл .env

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```
TELEGRAM_TOKEN=ваш_токен_бота
CHAT_ID=ваш_chat_id
```

## Запуск

### Вариант 1: Docker Compose (рекомендуется)

```bash
# Сборка и запуск
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### Вариант 2: Docker

```bash
# Сборка образа
docker build -t birthday-bot .

# Запуск контейнера
docker run -d \
  --name telegram-birthday-bot \
  --restart unless-stopped \
  -e TELEGRAM_TOKEN="ваш_токен" \
  -e CHAT_ID="ваш_chat_id" \
  -v birthday-bot-data:/app \
  birthday-bot

# Просмотр логов
docker logs -f telegram-birthday-bot

# Остановка
docker stop telegram-birthday-bot
docker rm telegram-birthday-bot
```

## Использование бота

После запуска бот будет автоматически проверять дни рождения каждый день в 09:00.

Доступные команды:
- `/start` - Показать приветственное сообщение
- `/check` - Проверить дни рождения вручную
- `/add <Имя> <Дата>` - Добавить день рождения (YYYY-MM-DD или DD.MM.YYYY)
- `/list` - Показать список всех дней рождения
- `/delete <ID>` - Удалить запись по ID
- `/status` - Показать статус бота

## Данные

База данных SQLite хранится в томе Docker `birthday-bot-data`, что обеспечивает сохранность данных при перезапуске контейнера.

## Переменные окружения

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `TELEGRAM_TOKEN` | Токен вашего Telegram бота | Да |
| `CHAT_ID` | ID чата для отправки уведомлений | Да |
| `DB_PATH` | Путь к базе данных (по умолчанию: /app/birthdays.db) | Нет |
