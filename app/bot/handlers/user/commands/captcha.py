"""Обработчик капчи для пользователей."""

import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from redis.asyncio import Redis

from app.core import get_logger, get_config
from app.database import get_session, crud
from app.database.models import CaptchaType
from app.services.captcha_service import send_captcha_to_user

logger = get_logger(__name__)
router = Router()


@router.callback_query(F.data.startswith("captcha:"))
async def handle_captcha_answer(callback: CallbackQuery) -> None:
    """
    Обработка ответа на капчу.

    Формат callback_data: captcha:user_id:selected_emoji
    """
    try:
        # Парсим callback_data
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer("❌ Ошибка капчи")
            return

        user_id = int(parts[1])
        selected_emoji = parts[2]

        # Проверяем, что отвечает тот же пользователь
        if callback.from_user.id != user_id:
            await callback.answer("⚠️ Это не ваша капча!")
            return

        config = get_config()

        # Пытаемся получить правильный ответ из Redis
        correct_answer = None
        attempts_count = 0

        # Сначала пытаемся Redis
        redis = None
        try:
            redis = Redis.from_url(config.redis_url, decode_responses=True)
            correct_answer = await redis.get(f"captcha:{user_id}")
            attempts_str = await redis.get(f"captcha_attempts:{user_id}")
            attempts_count = int(attempts_str or "0")
        except Exception:
            # Redis недоступен - используем in-memory store
            if 'in_memory_captcha_store' in globals():
                store = globals()['in_memory_captcha_store']
                if user_id in store:
                    correct_answer = store[user_id]['answer']
                    attempts_count = store[user_id]['attempts']
        finally:
            if redis:
                await redis.close()

        # Если не нашли ответ
        if not correct_answer:
            await callback.answer("⏳ Время капчи истекло!")
            return

        # Проверяем ответ
        is_correct = selected_emoji == correct_answer

        # Записываем попытку в БД
        from app.database.models import CaptchaType
        async for session in get_session():
            from app.database import crud
            await crud.create_captcha_attempt(
                session,
                user_id=user_id,
                chat_id=callback.message.chat.id,
                captcha_type=CaptchaType.EMOJI,
                is_successful=is_correct,
                attempts_count=attempts_count + 1
            )

        if is_correct:
            # Правильный ответ
            await callback.answer("✅ Верно! Ожидайте добавления в группу.")

            # Очищаем хранилище
            await clear_captcha_storage(user_id)

            logger.info(f"[id{user_id}] Капча пройдена успешно")

            # Вызываем обработку после капчи
            from app.bot.handlers.user.commands.join_requests import process_after_captcha
            asyncio.create_task(process_after_captcha(user_id, True))

        else:
            # Неправильный ответ
            attempts_count += 1

            # Обновляем счётчик попыток
            await update_captcha_attempts(user_id, attempts_count)

            if attempts_count >= config.captcha_max_attempts:
                # Превышено количество попыток
                await callback.answer("🚫 Превышено количество попыток!")

                # Очищаем хранилище
                await clear_captcha_storage(user_id)

                # Вызываем обработку после капчи (неудача)
                from app.bot.handlers.user.commands.join_requests import process_after_captcha
                asyncio.create_task(process_after_captcha(user_id, False))

                logger.info(f"[id{user_id}] Превышено количество попыток капчи: {attempts_count}")

            else:
                # Ещё есть попытки
                remaining = config.captcha_max_attempts - attempts_count
                await callback.answer(f"❌ Неверно! Осталось попыток: {remaining}")

    except Exception as e:
        logger.error(f"Ошибка в обработчике капчи: {e}", exc_info=True)
        try:
            await callback.answer("❌ Произошла ошибка")
        except Exception:
            pass


async def update_captcha_attempts(user_id: int, attempts: int) -> None:
    """Обновить счётчик попыток в Redis или памяти."""
    config = get_config()

    # Пытаемся Redis
    redis = None
    try:
        redis = Redis.from_url(config.redis_url, decode_responses=True)
        await redis.setex(f"captcha_attempts:{user_id}", 300, str(attempts))
        return
    except Exception:
        pass
    finally:
        if redis:
            await redis.close()

    # Fallback в памяти
    if 'in_memory_captcha_store' in globals():
        store = globals()['in_memory_captcha_store']
        if user_id in store:
            store[user_id]['attempts'] = attempts


async def clear_captcha_storage(user_id: int) -> None:
    """Очистить хранилище капчи для пользователя."""
    config = get_config()

    # Пытаемся Redis
    redis = None
    try:
        redis = Redis.from_url(config.redis_url, decode_responses=True)
        await redis.delete(f"captcha:{user_id}")
        await redis.delete(f"captcha_attempts:{user_id}")
    except Exception:
        pass
    finally:
        if redis:
            await redis.close()

    # Fallback в памяти
    if 'in_memory_captcha_store' in globals():
        store = globals()['in_memory_captcha_store']
        if user_id in store:
            del store[user_id]

@router.callback_query(F.data.startswith("captcha_resend:"))
async def resend_captcha(callback: CallbackQuery) -> None:
    """Переотправка капчи."""
    try:
        user_id = int(callback.data.split(":")[1])

        if callback.from_user.id != user_id:
            await callback.answer("⚠️ Это не ваша капча!")
            return

        await callback.answer("🔄 Отправляем новую капчу...")
        await send_captcha_to_user(callback.bot, user_id)

    except Exception as e:
        logger.error(f"Ошибка переотправки капчи: {e}")
        await callback.answer("❌ Ошибка")


