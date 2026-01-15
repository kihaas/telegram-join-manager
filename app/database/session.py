from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import get_config

# Глобальные объекты
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    """Инициализация подключения к БД."""
    global engine, async_session_factory

    config = get_config()

    # Определяем, это SQLite или нет
    is_sqlite = config.database_url.startswith("sqlite")

    # Параметры для engine (SQLite не поддерживает pool_size)
    engine_kwargs = {
        "echo": config.debug,
        "pool_pre_ping": True,
    }

    # Добавляем pool параметры только для не-SQLite БД
    if not is_sqlite:
        engine_kwargs.update({
            "pool_size": 10,
            "max_overflow": 20,
        })

    # Создаем async engine
    engine = create_async_engine(
        config.database_url,
        **engine_kwargs
    )

    # Создаем фабрику сессий
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии БД.

    Используется в handlers и services.

    Example:
        async def some_handler(session: AsyncSession = Depends(get_session)):
            ...
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Закрытие соединения с БД при завершении работы."""
    global engine
    if engine:
        await engine.dispose()