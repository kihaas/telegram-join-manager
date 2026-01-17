"""Сервис для отправки рассылок."""

import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards import get_back_to_menu
from app.core import get_logger, get_config
from app.database import get_session, crud

logger = get_logger(__name__)


async def send_broadcast(
        bot: Bot,
        user_id: int,
        text: str,
        photo_id: Optional[str] = None,
        markup: Optional[InlineKeyboardMarkup] = None,
        state: Optional[Any] = None
) -> None:
    """
    Отправка рассылки всем пользователям.

    Args:
        bot: Экземпляр бота
        user_id: ID админа для уведомлений
        text: Текст сообщения
        photo_id: file_id фото/видео (опционально)
        markup: Клавиатура с кнопками (опционально)
        state: Состояние FSM для отслеживания отмены
    """
    config = get_config()

    # Получаем всех пользователей
    async for session in get_session():
        user_ids = await crud.get_all_chat_ids(session)

    total_users = len(user_ids)
    successful = 0
    failed = 0
    cancelled = False

    logger.info(f"[id{user_id}] Запуск рассылки на {total_users} пользователей")

    # Создаём семафор для ограничения одновременных отправок
    semaphore = asyncio.Semaphore(config.broadcast_semaphore_limit)

    async def send_to_user(chat_id: int, username: Optional[str] = None) -> bool:
        """Отправить сообщение одному пользователю."""
        nonlocal successful, failed, cancelled

        # Проверяем отмену
        if state:
            data = await state.get_data()
            if data.get('broadcast_cancelled'):
                cancelled = True
                return False

        if cancelled:
            return False

        async with semaphore:
            try:
                # Персонализируем текст
                personalized_text = text
                if username:
                    personalized_text = personalized_text.replace("{username}", f"@{username}")

                # {name} заменяем на "Пользователь", т.к. имени нет в БД
                personalized_text = personalized_text.replace("{name}", "Пользователь")

                # Отправляем сообщение
                if photo_id:
                    if photo_id.startswith("AgAC"):  # Это фото
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=photo_id,
                            caption=personalized_text,
                            reply_markup=markup
                        )
                    else:  # Это видео
                        await bot.send_video(
                            chat_id=chat_id,
                            video=photo_id,
                            caption=personalized_text,
                            reply_markup=markup
                        )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=personalized_text,
                        reply_markup=markup
                    )

                successful += 1

                # Задержка между сообщениями
                await asyncio.sleep(config.broadcast_delay)
                return True

            except TelegramForbiddenError:
                # Пользователь заблокировал бота
                logger.info(f"[broadcast] Пользователь {chat_id} заблокировал бота")
                failed += 1
                return False

            except TelegramBadRequest as e:
                # Некорректный chat_id или другие ошибки
                if "chat not found" in str(e).lower() or "user not found" in str(e).lower():
                    logger.info(f"[broadcast] Пользователь {chat_id} не найден")
                else:
                    logger.warning(f"[broadcast] Ошибка для {chat_id}: {e}")
                failed += 1
                return False

            except TelegramRetryAfter as e:
                # Флуд-контроль
                logger.warning(f"[broadcast] Флуд-контроль для {chat_id}: ждём {e.retry_after} сек")
                await asyncio.sleep(e.retry_after)
                # Пробуем ещё раз
                return await send_to_user(chat_id, username)

            except Exception as e:
                # Любая другая ошибка
                logger.error(f"[broadcast] Неизвестная ошибка для {chat_id}: {e}")
                failed += 1

                # Повторная попытка
                for attempt in range(config.broadcast_retry_attempts):
                    try:
                        await asyncio.sleep(1)  # Ждём перед повторной попыткой
                        if photo_id:
                            if photo_id.startswith("AgAC"):
                                await bot.send_photo(
                                    chat_id=chat_id,
                                    photo=photo_id,
                                    caption=personalized_text,
                                    reply_markup=markup
                                )
                            else:
                                await bot.send_video(
                                    chat_id=chat_id,
                                    video=photo_id,
                                    caption=personalized_text,
                                    reply_markup=markup
                                )
                        else:
                            await bot.send_message(
                                chat_id=chat_id,
                                text=personalized_text,
                                reply_markup=markup
                            )

                        successful += 1
                        failed -= 1
                        return True

                    except Exception:
                        if attempt == config.broadcast_retry_attempts - 1:
                            return False

                return False

    # Отправляем всем пользователям
    tasks = []
    for chat_id in user_ids:
        # Получаем username из БД если нужно
        username = None
        if "{username}" in text:
            async for session in get_session():
                user = await crud.get_user_by_chat_id(session, chat_id)
                if user and user.username:
                    username = user.username

        task = asyncio.create_task(send_to_user(chat_id, username))
        tasks.append(task)

    # Ждём завершения всех задач
    await asyncio.gather(*tasks, return_exceptions=True)

    # Отправляем итоговую статистику админу
    result_text = (
        "📊 <b>Рассылка завершена</b>\n\n"
        f"✅ <b>Успешно отправлено:</b> <code>{successful}</code>\n"
        f"❌ <b>Не удалось отправить:</b> <code>{failed}</code>\n"
        f"📈 <b>Всего получателей:</b> <code>{total_users}</code>\n\n"
    )

    if cancelled:
        result_text += "⚠️ <i>Рассылка была прервана</i>\n"

    if failed > 0:
        result_text += "🔍 <i>Не отправлено: заблокировавшие бота или неверные ID</i>\n"

    try:
        await bot.send_message(user_id, result_text, reply_markup=get_back_to_menu())
    except Exception as e:
        logger.error(f"Не удалось отправить статистику админу {user_id}: {e}")

    logger.info(f"[id{user_id}] Рассылка завершена: {successful}/{total_users} успешно")

    # Очищаем состояние
    if state:
        await state.clear()