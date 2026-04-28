# Руководство по развёртыванию

## Требования

- Python 3.11–3.13
- redis (6.x–7.x)
- sqlite3 (встроенный) или PostgreSQL/MySQL
- aiogram 3.x

## Установка зависимостей

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# или source .venv/bin/activate  # Linux/macOS

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Настройка .env

Создай файл `.env` в корне проекта:

```env
BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
DEVELOPERS=123456788
ADMIN_IDS=123456788
DATABASE_URL=sqlite+aiosqlite:///data/applications.db
REDIS_URL=redis://redis:6379/0
LOG_FILE=logs/app.log
LOG_LEVEL=INFO
DEBUG=false
```

## Запуск бота

```bash
.venv\Scripts\python.exe main.py
```

Бот будет:
- запускать бота через `aiogram`.
- инициализировать БД (`applications.db`).
- использовать Redis как хранилище FSM.

## Рекомендации по нагрузке

- Один бот — до 1000 join‑запросов в час.
- При большей нагрузке используй несколько ботов и балансировку.
- В продакшене используй PostgreSQL/MySQL вместо SQLite и настрой репликацию.