"""Точка входа в приложение."""

import asyncio
import sys
from contextlib import suppress

from app.core import load_config, setup_logger, get_logger

# Фикс для Windows event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main() -> None:
    """Основная функция запуска бота."""

    # 1. Загружаем конфигурацию
    try:
        config = load_config()
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        sys.exit(1)

    # 2. Настраиваем логирование
    logger = setup_logger(log_file=config.log_file, log_level=config.log_level)
    logger.info("🚀 Запуск telegram-join-manager...")
    logger.info(f"📝 Режим отладки: {'включён' if config.debug else 'выключён'}")
    logger.info(f"🔧 Уровень логирования: {config.log_level}")

    # Проверяем критичные настройки
    if not config.bot_token:
        logger.error("❌ BOT_TOKEN не найден в .env файле!")
        sys.exit(1)

    if not config.developers:
        logger.warning("⚠️ DEVELOPERS не указаны — бот запускается без администраторов!")

    logger.info(f"👑 Разработчики: {config.developers}")
    logger.info(f"👤 Администраторы: {config.admin_ids}")
    logger.info(f"💾 База данных: {config.database_url}")
    logger.info(f"🔴 Redis: {config.redis_url}")

    # 3. Инициализация базы данных
    from app.database import init_db, close_db

    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        sys.exit(1)

    # # 3. Инициализация базы данных
    # from app.database import init_db, close_db
    # try:
    #     init_db()
    #     logger.info("✅ База данных инициализирована")
    #
    #     # Только проверяем БД, НЕ запускаем миграции автоматически
    #     from app.database.migrations import get_database_info_sync
    #     db_info = get_database_info_sync()
    #     logger.info(f"📊 Таблицы: {', '.join(db_info['tables'])}")
    #     logger.info(f"👥 Пользователей: {db_info['users_count']}")
    #     logger.info(f"📅 Диапазон дат: {db_info['oldest_date']} - {db_info['newest_date']}")
    #
    #     if db_info['today_count'] == db_info['users_count'] and db_info['users_count'] > 0:
    #         logger.warning("⚠️ ВСЕ пользователи имеют сегодняшнюю дату! Миграция уже была применена.")
    #
    # except Exception as e:
    #     logger.error(f"❌ Ошибка инициализации БД: {e}")
    #     sys.exit(1)

    # 5. Запуск бота
    from app.bot import start_bot

    try:
        await start_bot()
    except KeyboardInterrupt:
        logger.info("⏸️ Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Закрываем соединения при завершении
        await close_db()
        logger.info("👋 Все соединения закрыты")


if __name__ == "__main__":
    with suppress(KeyboardInterrupt, asyncio.CancelledError):
        asyncio.run(main())