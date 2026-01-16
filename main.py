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

    # # 4. Проверка и применение миграций
    # logger.info("🔄 Проверка миграций Alembic...")
    # try:
    #     from alembic.config import Config as AlembicConfig
    #     from alembic import command
    #
    #     alembic_cfg = AlembicConfig("alembic.ini")
    #     command.upgrade(alembic_cfg, "head")
    #     logger.info("✅ Миграции применены")
    # except ImportError as e:
    #     logger.warning(f"⚠️ Alembic не установлен: {e}")
    #     logger.info("💡 Установи: pip install alembic")
    #
    #
    # logger.info("✅ Инициализация завершена!")

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