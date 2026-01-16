"""Обработчик капчи."""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.core import get_logger
from app.database import get_session
from app.services.captcha import (
    verify_captcha_answer,
    handle_captcha_failure,
    send_welcome_after_captcha
)

logger = get_logger(__name__)
router = Router(name="captcha_router")

# Хранилище попыток пользователей (в production лучше использовать Redis)
user_attempts: dict[int, int] = {}


@router.callback_query(F.data.startswith("captcha:"))
async def handle_captcha_callback(callback: CallbackQuery) -> None:
    """
    Обработка ответа на капчу.

    Формат callback_data: captcha:user_id:выбранный_emoji:правильный_emoji
    """
    await callback.answer()

    try:
        # Парсим callback_data
        _, str_user_id, user_answer, correct_answer = callback.data.split(":")
        user_id = int(str_user_id)

        # Проверяем, что это именно тот пользователь
        if user_id != callback.from_user.id:
            await callback.answer("❌ Эта капча предназначена не для вас", show_alert=True)
            return

        # Получаем количество попыток
        attempts = user_attempts.get(user_id, 0) + 1
        user_attempts[user_id] = attempts

        # Удаляем сообщение с капчей
        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning(f"[id{user_id}] Не удалось удалить сообщение с капчей: {e}")

        # Проверяем ответ
        async for session in get_session():
            is_correct = await verify_captcha_answer(
                session=session,
                user_id=user_id,
                chat_id=callback.message.chat.id,
                user_answer=user_answer,
                correct_answer=correct_answer,
                attempts_count=attempts
            )

        if is_correct:
            # Правильный ответ!
            await callback.message.answer(
                "✅ <b>Правильно!</b>\n\n"
                "Вы успешно прошли проверку безопасности."
            )

            # Отправляем приветствие
            await send_welcome_after_captcha(callback.bot, user_id)

            # Очищаем попытки
            user_attempts.pop(user_id, None)

            logger.info(f"[id{user_id}] Капча пройдена успешно")

        else:
            # Неправильный ответ
            await handle_captcha_failure(
                bot=callback.bot,
                user_id=user_id,
                chat_id=callback.message.chat.id,
                attempts=attempts
            )

    except ValueError as e:
        logger.error(f"Ошибка парсинга callback_data: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка обработки ответа. Попробуйте ещё раз."
        )
    except Exception as e:
        logger.error(f"Ошибка обработки капчи: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Произошла ошибка. Попробуйте ещё раз или обратитесь к администратору."
        )