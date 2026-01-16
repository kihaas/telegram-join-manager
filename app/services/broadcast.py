import asyncio
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_logger, get_config
from app.database import crud
from app.database.models import BroadcastStatus, BroadcastDraft

logger = get_logger(__name__)


async def send_broadcast(
        bot: Bot,
        session: AsyncSession,
        draft_id: int,
        test_user_id: Optional[int] = None
) -> dict:
    """
    Запустить рассылку.

    Args:
        bot: Экземпляр бота
        session: Сессия БД
        draft_id: ID черновика рассылки
        test_user_id: Если указан, отправит только этому пользователю (тестовая рассылка)

    Returns:
        dict с результатами: {success: int, failed: int, total: int}
    """
    config = get_config()

    # Получаем черновик
    draft = await session.get(BroadcastDraft, draft_id)
    if not draft:
        logger.error(f"Черновик {draft_id} не найден")
        return {"success": 0, "failed": 0, "total": 0}

    # Получаем список пользователей
    if test_user_id:
        chat_ids = [test_user_id]
    else:
        chat_ids = await crud.get_all_chat_ids(session)

    total = len(chat_ids)
    success = 0
    failed = 0

    # Обновляем статус на "отправляется"
    if not test_user_id:
        await crud.update_broadcast_status(
            session,
            draft_id,
            BroadcastStatus.SENDING,
            total_users=total
        )
        await session.commit()

    # Семафор для ограничения одновременных запросов
    semaphore = asyncio.Semaphore(config.broadcast_semaphore_limit)

    async def send_to_user(chat_id: int) -> bool:
        """Отправить сообщение одному пользователю."""
        async with semaphore:
            try:
                # Задержка между отправками
                await asyncio.sleep(config.broadcast_delay)

                # Отправляем сообщение
                if draft.media_id:
                    # С медиа
                    if draft.media_id.startswith("AgAC"):  # Фото
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=draft.media_id,
                            caption=draft.text
                        )
                    else:  # Видео или документ
                        await bot.send_video(
                            chat_id=chat_id,
                            video=draft.media_id,
                            caption=draft.text
                        )
                else:
                    # Только текст
                    await bot.send_message(
                        chat_id=chat_id,
                        text=draft.text
                    )

                return True

            except TelegramForbiddenError:
                # Пользователь заблокировал бота
                logger.debug(f"[id{chat_id}] Заблокировал бота")
                return False

            except TelegramBadRequest as e:
                logger.warning(f"[id{chat_id}] Ошибка отправки: {e}")
                return False

            except Exception as e:
                logger.error(f"[id{chat_id}] Неизвестная ошибка: {e}")
                return False

    # Запускаем рассылку
    tasks = [send_to_user(chat_id) for chat_id in chat_ids]
    results = await asyncio.gather(*tasks)

    success = sum(results)
    failed = total - success

    # Обновляем статистику
    if not test_user_id:
        await crud.update_broadcast_status(
            session,
            draft_id,
            BroadcastStatus.COMPLETED,
            successful_sends=success,
            failed_sends=failed
        )
        await session.commit()

    logger.info(
        f"Рассылка {draft_id} завершена: "
        f"✅ {success} | ❌ {failed} | Всего: {total}"
    )

    return {
        "success": success,
        "failed": failed,
        "total": total
    }


async def cancel_broadcast(session: AsyncSession, draft_id: int) -> bool:
    """
    Отменить рассылку.

    Args:
        session: Сессия БД
        draft_id: ID черновика

    Returns:
        True если отменена, False если ошибка
    """
    draft = await session.get(BroadcastDraft, draft_id)

    if not draft:
        return False

    if draft.status != BroadcastStatus.SENDING:
        return False

    await crud.update_broadcast_status(
        session,
        draft_id,
        BroadcastStatus.CANCELLED
    )
    await session.commit()

    logger.info(f"Рассылка {draft_id} отменена")
    return True