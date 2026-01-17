"""Инициализация бота и диспетчера."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from raito import Raito
from raito.utils.configuration import RaitoConfiguration
from raito.plugins.roles import RoleManager
from raito.plugins.roles.providers.sql.sqlite import SQLiteRoleProvider
from raito.utils.storages.sql.sqlite import SQLiteStorage as RaitoSQLiteStorage

from app.core import get_config, get_logger
from app.bot.middlewares import LoggingMiddleware, ThrottlingMiddleware
from app.bot.handlers import main_router
from app.bot.handlers.admin.commands.welcome import router as welcome_router

logger = get_logger(__name__)


async def create_bot() -> Bot:
    """Создание экземпляра бота."""
    config = get_config()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True
        )
    )

    bot_info = await bot.get_me()
    logger.info(f"✅ Бот создан: @{bot_info.username}")
    return bot


async def create_dispatcher() -> Dispatcher:
    """Создание диспетчера с Redis storage."""
    config = get_config()

    # Redis для FSM storage
    try:
        redis = Redis.from_url(config.redis_url, decode_responses=True)
        await redis.ping()
        storage = RedisStorage(redis)
        logger.info("✅ Redis подключён для FSM storage")
    except Exception as e:
        logger.warning(f"⚠️ Redis недоступен: {e}. Используется MemoryStorage")
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # Регистрируем middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.chat_join_request.middleware(LoggingMiddleware())

    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))

    logger.info("✅ Middlewares зарегистрированы")

    return dp


async def setup_raito(bot: Bot, dp: Dispatcher) -> Raito:
    """
    Настройка Raito для управления ролями.

    Returns:
        Настроенный экземпляр Raito
    """
    config = get_config()

    # Определяем путь к БД для raito
    db_path = config.database_url.replace("sqlite+aiosqlite:///", "")

    # Storage для raito
    raito_storage = RaitoSQLiteStorage(f"sqlite+aiosqlite:///{db_path}")

    # Role Manager
    role_manager = RoleManager(
        SQLiteRoleProvider(raito_storage),
        developers=config.developers
    )

    # Создаём Raito с указанием директории роутеров
    raito = Raito(
        dispatcher=dp,
        routers_dir="app/bot/handlers",  # Указываем директорию с роутерами
        developers=config.developers,
        configuration=RaitoConfiguration(role_manager=role_manager),
    )

    # Сохраняем raito в контекстных данных диспетчера
    dp["raito"] = raito

    await raito.setup()

    logger.info(f"✅ Raito настроен. Разработчики: {config.developers}")

    return raito


async def start_bot() -> None:
    """Главная функция запуска бота."""
    logger.info("🚀 Запуск бота...")

    # Создаём бота и диспетчер
    bot = await create_bot()
    dp = await create_dispatcher()

    # Настраиваем Raito
    raito = await setup_raito(bot, dp)

    # Удаляем webhook и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("📡 Polling запущен. Бот работает!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("🛑 Бот остановлен")


__all__ = [
    "create_bot",
    "create_dispatcher",
    "setup_raito",
    "start_bot",
]