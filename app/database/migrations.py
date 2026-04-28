"""Скрипт для применения миграций Alembic."""

import sys
from pathlib import Path

# Добавляем путь к корню проекта
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alembic import command  # type: ignore
from alembic.config import Config as AlembicConfig  # type: ignore

from app.core import load_config, setup_logger

if __name__ == "__main__":
    # Указываем путь к .env вручную
    env_path = project_root / ".env"

    # Загружаем конфиг с указанием пути
    try:
        import os
        os.environ['ENV_FILE'] = str(env_path)

        config = load_config()
        logger = setup_logger(log_file=config.log_file, log_level=config.log_level)
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        print(f"📁 Искал файл: {env_path}")
        print(f"📁 Текущая директория: {Path.cwd()}")
        sys.exit(1)

    # Применяем миграции
    logger.info("🔄 Применение миграций Alembic...")

    try:
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Миграции успешно применены!")
    except Exception as e:
        logger.error(f"❌ Ошибка применения миграций: {e}")
        sys.exit(1)

# """
# Миграции базы данных для исправления проблем.
# """
#
# import asyncio
# import sys
# import os
# from datetime import datetime
# from pathlib import Path
#
# # Добавляем путь к проекту
# project_root = Path(__file__).resolve().parent.parent.parent
# sys.path.insert(0, str(project_root))
#
# # Загружаем .env вручную
# from dotenv import load_dotenv
# env_path = project_root / '.env'
# if env_path.exists():
#     load_dotenv(env_path)
#     print(f"✅ Загружен .env файл: {env_path}")
# else:
#     print(f"⚠️ .env файл не найден: {env_path}")
#
# # Импортируем СИНХРОННЫЙ SQLAlchemy для миграций
# from sqlalchemy import create_engine, text
#
# # Импортируем после загрузки .env
# from app.core import load_config
#
# print("=" * 50)
# print("🚀 Запуск миграций базы данных")
# print("=" * 50)
#
#
# def run_migrations_sync() -> None:
#     """Запуск всех миграций (синхронная версия)."""
#     # Загружаем конфиг
#     config = load_config()
#
#     print(f"📁 База данных из конфига: {config.database_url}")
#
#     # Преобразуем путь к абсолютному
#     db_url = config.database_url
#
#     # Если это SQLite с относительным путем
#     if db_url.startswith("sqlite+aiosqlite:///"):
#         # Извлекаем относительный путь
#         rel_path = db_url.replace("sqlite+aiosqlite:///", "")
#         # Преобразуем в абсолютный путь
#         abs_path = (project_root / rel_path).resolve()
#         print(f"📂 Относительный путь: {rel_path}")
#         print(f"📂 Абсолютный путь: {abs_path}")
#
#         # Проверяем существует ли файл
#         if not abs_path.exists():
#             print(f"⚠️ Файл БД не найден: {abs_path}")
#             print(f"🔍 Ищем в: {project_root}")
#             # Покажи что есть в директории
#             data_dir = project_root / "data"
#             if data_dir.exists():
#                 print(f"📁 Содержимое data/: {list(data_dir.glob('*'))}")
#             else:
#                 print(f"❌ Директория data не существует")
#                 # Создаём директорию
#                 data_dir.mkdir(exist_ok=True)
#                 print(f"✅ Создана директория data")
#
#         # Используем абсолютный путь для SQLite
#         db_url = f"sqlite:///{abs_path}"
#
#     print(f"🔗 Финальный URL: {db_url}")
#
#     # Создаём СИНХРОННЫЙ engine
#     engine = create_engine(db_url, echo=True)
#
#     try:
#         with engine.begin() as conn:  # Синхронный контекст
#             _migrate_001_check_tables(conn)
#             _migrate_002_fix_dates(conn)
#             _migrate_003_add_indexes(conn)
#
#         print("✅ Все миграции успешно применены")
#
#     except Exception as e:
#         print(f"❌ Ошибка миграции: {e}")
#         import traceback
#         traceback.print_exc()
#         raise
#
#
# def _migrate_001_check_tables(conn) -> None:
#     """
#     Миграция 1: Проверка и создание недостающих таблиц.
#     """
#     print("\n1️⃣ Проверка таблиц...")
#
#     # Таблицы которые должны быть
#     required_tables = [
#         ('users', '''
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username VARCHAR(255),
#                 chat_id INTEGER UNIQUE NOT NULL,
#                 registration_date VARCHAR(50) NOT NULL
#             )
#         '''),
#         ('admin', '''
#             CREATE TABLE IF NOT EXISTS admin (
#                 id INTEGER PRIMARY KEY,
#                 applications INTEGER DEFAULT 0,
#                 photo TEXT,
#                 buttons TEXT DEFAULT '[]'
#             )
#         '''),
#         ('pending_requests', '''
#             CREATE TABLE IF NOT EXISTS pending_requests (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id INTEGER NOT NULL,
#                 username VARCHAR(255),
#                 first_name VARCHAR(255),
#                 chat_id INTEGER NOT NULL,
#                 request_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                 status VARCHAR(20) NOT NULL DEFAULT 'pending',
#                 processed_at DATETIME,
#                 processed_by INTEGER
#             )
#         '''),
#         ('captcha_attempts', '''
#             CREATE TABLE IF NOT EXISTS captcha_attempts (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id INTEGER NOT NULL,
#                 chat_id INTEGER NOT NULL,
#                 captcha_type VARCHAR(20) NOT NULL,
#                 is_successful BOOLEAN NOT NULL,
#                 attempt_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#                 attempts_count INTEGER DEFAULT 1
#             )
#         ''')
#     ]
#
#     for table_name, create_sql in required_tables:
#         # Проверяем существует ли таблица
#         result = conn.execute(
#             text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
#         )
#
#         if not result.fetchone():
#             print(f"   ↳ Создаём таблицу {table_name}")
#             conn.execute(text(create_sql))
#         else:
#             print(f"   ↳ Таблица {table_name} ✓")
#
#     print("✅ Таблицы проверены")
#
#
# def _migrate_002_fix_dates(conn) -> None:
#     """
#     Миграция 2: Исправление формата дат в таблице users.
#     """
#     print("\n2️⃣ Исправление дат пользователей...")
#
#     # Проверяем есть ли таблица users
#     result = conn.execute(
#         text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
#     )
#     if not result.fetchone():
#         print("⚠️ Таблица users не найдена, пропускаем")
#         return
#
#     # Получаем количество пользователей
#     result = conn.execute(text("SELECT COUNT(*) FROM users"))
#     total_users = result.fetchone()[0]
#     print(f"   ↳ Всего пользователей: {total_users}")
#
#     if total_users == 0:
#         print("   ↳ Нет пользователей в базе")
#         return
#
#     # Исправляем все даты на сегодня
#     today = datetime.now().strftime("%d.%m.%Y")
#     print(f"   ↳ Устанавливаем дату: {today}")
#
#     # Обновляем ВСЕ даты на сегодня
#     try:
#         result = conn.execute(
#             text(f"UPDATE users SET registration_date = '{today}'")
#         )
#         updated_count = result.rowcount
#         print(f"   ↳ Обновлено записей: {updated_count}")
#     except Exception as e:
#         print(f"   ↳ Ошибка обновления: {e}")
#
#     print("✅ Даты исправлены")
#
#
# def _migrate_003_add_indexes(conn) -> None:
#     """
#     Миграция 3: Добавление индексов для производительности.
#     """
#     print("\n3️⃣ Добавление индексов...")
#
#     indexes = [
#         ("idx_users_registration_date",
#          "CREATE INDEX IF NOT EXISTS idx_users_registration_date ON users(registration_date)"),
#         ("idx_users_chat_id",
#          "CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id)"),
#         ("idx_pending_requests_status",
#          "CREATE INDEX IF NOT EXISTS idx_pending_requests_status ON pending_requests(status)"),
#         ("idx_pending_requests_user_id",
#          "CREATE INDEX IF NOT EXISTS idx_pending_requests_user_id ON pending_requests(user_id)"),
#         ("idx_pending_requests_time",
#          "CREATE INDEX IF NOT EXISTS idx_pending_requests_time ON pending_requests(request_time)"),
#         ("idx_captcha_user_time",
#          "CREATE INDEX IF NOT EXISTS idx_captcha_user_time ON captcha_attempts(user_id, attempt_time)"),
#     ]
#
#     created = 0
#     for idx_name, idx_sql in indexes:
#         try:
#             conn.execute(text(idx_sql))
#             print(f"   ↳ Добавлен индекс: {idx_name}")
#             created += 1
#         except Exception as e:
#             print(f"   ↳ Не удалось создать индекс {idx_name}: {e}")
#
#     print(f"✅ Добавлено индексов: {created}/{len(indexes)}")
#
#
# def get_database_info_sync() -> dict:
#     """Получить информацию о базе данных (синхронная версия)."""
#     config = load_config()
#
#     # Преобразуем путь к абсолютному
#     db_url = config.database_url
#     if db_url.startswith("sqlite+aiosqlite:///"):
#         rel_path = db_url.replace("sqlite+aiosqlite:///", "")
#         abs_path = (project_root / rel_path).resolve()
#         db_url = f"sqlite:///{abs_path}"
#
#     engine = create_engine(db_url, echo=False)
#
#     info = {
#         'tables': [],
#         'users_count': 0,
#         'oldest_date': None,
#         'newest_date': None,
#         'today_count': 0
#     }
#
#     try:
#         with engine.begin() as conn:
#             # Список таблиц
#             result = conn.execute(
#                 text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
#             )
#             info['tables'] = [row[0] for row in result.fetchall()]
#
#             # Статистика users
#             if 'users' in info['tables']:
#                 # Количество пользователей
#                 result = conn.execute(text("SELECT COUNT(*) FROM users"))
#                 info['users_count'] = result.fetchone()[0]
#
#                 # Минимальная и максимальная дата
#                 result = conn.execute(
#                     text("""
#                         SELECT MIN(registration_date), MAX(registration_date)
#                         FROM users
#                         WHERE registration_date IS NOT NULL
#                         AND registration_date != ''
#                     """)
#                 )
#                 row = result.fetchone()
#                 if row and row[0] and row[1]:
#                     info['oldest_date'] = row[0]
#                     info['newest_date'] = row[1]
#
#                 # Пользователей с сегодняшней датой
#                 today = datetime.now().strftime("%d.%m.%Y")
#                 result = conn.execute(
#                     text(f"SELECT COUNT(*) FROM users WHERE registration_date = '{today}'")
#                 )
#                 info['today_count'] = result.fetchone()[0]
#
#     except Exception as e:
#         print(f"Ошибка получения информации о БД: {e}")
#
#     return info
#
#
# def main():
#     """Основная функция для запуска из командной строки."""
#     try:
#         # Показываем информацию о путях
#         print(f"📁 Корень проекта: {project_root}")
#         print(f"📁 Текущая директория: {Path.cwd()}")
#
#         # Запускаем миграции
#         print("\n🔄 Применение миграций...")
#         run_migrations_sync()
#
#         # Получаем информацию ПОСЛЕ миграций
#         print("\n📊 Информация о базе ПОСЛЕ миграций:")
#         db_info_after = get_database_info_sync()
#         print(f"   Таблицы: {', '.join(db_info_after['tables'])}")
#         print(f"   Пользователей: {db_info_after['users_count']}")
#         print(f"   Диапазон дат: {db_info_after['oldest_date']} - {db_info_after['newest_date']}")
#         print(f"   Сегодняшних: {db_info_after['today_count']}")
#
#         print("\n✅ Миграции успешно завершены!")
#
#     except Exception as e:
#         print(f"\n❌ Ошибка: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)
#
#
# if __name__ == "__main__":
#     main()