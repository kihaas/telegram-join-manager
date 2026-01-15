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

    # 4. Проверка и применение миграций
    logger.info("🔄 Проверка миграций Alembic...")
    try:
        from alembic import command  # type: ignore
        from alembic.config import Config as AlembicConfig  # type: ignore

        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Миграции применены")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось применить миграции: {e}")
        logger.info("💡 Запусти вручную: alembic upgrade head")

    # TODO: Следующие шаги:
    # 5. Создание бота и диспетчера
    # 6. Настройка Raito (роли)
    # 7. Регистрация middlewares
    # 8. Регистрация handlers
    # 9. Запуск polling

    logger.info("✅ Инициализация завершена!")
    logger.info("🔄 Следующий шаг: создание bot модуля с Raito...")

    # Временная заглушка
    logger.info("⏸️ Бот готов к дальнейшей разработке")
    await asyncio.sleep(1)

    # Закрываем соединения
    await close_db()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt, asyncio.CancelledError):
        asyncio.run(main())