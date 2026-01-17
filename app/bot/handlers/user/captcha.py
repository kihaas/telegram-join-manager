from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from app.core import get_logger
from app.services.captcha import handle_captcha_callback

logger = get_logger(__name__)
router = Router()


@router.callback_query(F.data.startswith("captcha:"))
async def process_captcha_callback(callback: CallbackQuery):
    """
    Обработка callback от inline-кнопки капчи.

    Callback data формат: captcha:user_id:emoji:правильный_ответ
    """
    user_id = callback.from_user.id

    logger.info(f"[id{user_id}] Callback капчи: {callback.data}")

    try:
        # Обрабатываем капчу через сервис
        is_correct = await handle_captcha_callback(
            bot=callback.bot,
            callback_data=callback.data,
            user_id=user_id
        )

        # Удаляем inline-клавиатуру после ответа
        if is_correct:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except TelegramBadRequest:
                # Если не удалось изменить сообщение, просто игнорируем
                pass

        await callback.answer()

    except Exception as e:
        logger.error(f"[id{user_id}] Ошибка обработки callback капчи: {e}")
        await callback.answer("❌ Ошибка обработки", show_alert=False)