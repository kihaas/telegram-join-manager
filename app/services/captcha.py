import os
import random
from pathlib import Path
from typing import List, Tuple, Optional

from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_logger, get_config
from app.database import crud
from app.database.models import CaptchaType

from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)

CAPTCHA_BASE_PATH = Path(os.getenv("CAPTCHA_IMAGE_PATH", "assets/"))

CAPTCHA_VARIANTS = [
    (CAPTCHA_BASE_PATH / "smile_1.png", "😄", ["😄", "😎", "⭐", "🤖"]),
    (CAPTCHA_BASE_PATH / "smile_2.png", "😎", ["😄", "😎", "⭐", "🤖"]),
    (CAPTCHA_BASE_PATH / "smile_3.png", "⭐", ["😄", "😎", "⭐", "🤖"]),
]

def get_random_captcha() -> Tuple[str, str, List[str]]:
    """
    Получить случайный вариант капчи.

    Returns:
        Tuple[путь_к_картинке, правильный_ответ, список_вариантов]
    """
    image_path, correct_emoji, variants = random.choice(CAPTCHA_VARIANTS)

    # Перемешиваем варианты для рандомного порядка кнопок
    shuffled_variants = variants.copy()
    random.shuffle(shuffled_variants)

    return image_path, correct_emoji, shuffled_variants


def build_captcha_keyboard(variants: List[str], user_id: int, correct_answer: str) -> InlineKeyboardMarkup:
    """
    Создать inline-клавиатуру с вариантами капчи.

    Args:
        variants: Список эмодзи для кнопок
        user_id: ID пользователя (для callback_data)
        correct_answer: Правильный ответ

    Returns:
        InlineKeyboardMarkup с кнопками
    """
    builder = InlineKeyboardBuilder()

    # Создаём кнопки по 2 в ряд
    for i in range(0, len(variants), 2):
        row_variants = variants[i:i + 2]
        buttons = []

        for emoji in row_variants:
            # В callback_data передаём: captcha:user_id:emoji:правильный_ответ
            callback_data = f"captcha:{user_id}:{emoji}:{correct_answer}"
            buttons.append(InlineKeyboardButton(text=emoji, callback_data=callback_data))

        builder.row(*buttons)

    return builder.as_markup()


async def send_captcha_to_user(bot, user_id: int) -> Optional[Tuple[str, str]]:
    """
    Отправить капчу пользователю.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя

    Returns:
        Tuple[правильный_ответ, путь_к_картинке] или None при ошибке
    """
    try:
        # Получаем случайную капчу
        image_path, correct_answer, variants = get_random_captcha()

        # Проверяем существование файла
        if not Path(image_path).exists():
            logger.error(f"Файл капчи не найден: {image_path}")
            return None

        # Создаём клавиатуру
        keyboard = build_captcha_keyboard(variants, user_id, correct_answer)

        # Отправляем картинку с капчей
        photo = FSInputFile(image_path)

        caption = (
            "🔐 <b>Проверка безопасности</b>\n\n"
            "Выберите эмодзи, которое изображено на картинке:\n\n"
            "⚠️ <i>Отвечая, вы соглашаетесь на получение сообщений от бота</i>"
        )

        await bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=caption,
            reply_markup=keyboard
        )

        logger.info(f"[id{user_id}] Капча отправлена: {correct_answer}")
        return correct_answer, image_path

    except Exception as e:
        logger.error(f"[id{user_id}] Ошибка отправки капчи: {e}")
        return None


async def verify_captcha_answer(
        session: AsyncSession,
        user_id: int,
        chat_id: int,
        user_answer: str,
        correct_answer: str,
        attempts_count: int = 1
) -> bool:
    """
    Проверить ответ на капчу и записать в БД.

    Args:
        session: Сессия БД
        user_id: ID пользователя
        chat_id: ID чата
        user_answer: Ответ пользователя
        correct_answer: Правильный ответ
        attempts_count: Номер попытки

    Returns:
        True если ответ правильный, False если нет
    """
    is_correct = user_answer == correct_answer

    # Записываем попытку в БД
    await crud.create_captcha_attempt(
        session=session,
        user_id=user_id,
        chat_id=chat_id,
        captcha_type=CaptchaType.IMAGE,
        is_successful=is_correct,
        attempts_count=attempts_count
    )

    logger.info(
        f"[id{user_id}] Капча: {'✅ правильно' if is_correct else '❌ неправильно'} "
        f"(попытка {attempts_count}/3)"
    )

    return is_correct


async def handle_captcha_failure(bot, user_id: int, chat_id: int, attempts: int) -> None:
    """
    Обработать провал капчи.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        chat_id: ID чата
        attempts: Количество попыток
    """
    config = get_config()

    if attempts >= config.captcha_max_attempts:
        # Бан после 3 провалов
        try:
            from raito import Raito
            raito: Raito = bot.get("raito")

            # Баним пользователя
            await raito.role_manager.assign_role(bot.id, bot.id, user_id, "tester")

            # Кикаем из чата
            from aiogram.types import ChatMemberBanned
            await bot.ban_chat_member(chat_id, user_id)

            await bot.send_message(
                user_id,
                "❌ <b>Вы были забанены</b>\n\n"
                "Вы не прошли проверку безопасности и были исключены из группы.\n"
                f"Попыток: {attempts}/{config.captcha_max_attempts}"
            )

            logger.warning(f"[id{user_id}] Забанен за провал капчи ({attempts} попыток)")

        except Exception as e:
            logger.error(f"[id{user_id}] Ошибка бана: {e}")

    else:
        # Даём ещё попытку
        await bot.send_message(
            user_id,
            f"❌ <b>Неправильно!</b>\n\n"
            f"Попробуйте ещё раз.\n"
            f"Попыток осталось: {config.captcha_max_attempts - attempts}"
        )

        # Отправляем новую капчу
        await send_captcha_to_user(bot, user_id)


async def send_welcome_after_captcha(bot, user_id: int) -> None:
    """
    Отправить приветствие после успешной капчи.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
    """
    from app.database import get_session, crud

    try:
        # Получаем настройки приветствия (settings_id=2)
        async for session in get_session():
            settings = await crud.get_admin_settings(session, settings_id=2)

        if settings and settings.photo:
            # Есть медиа
            text = settings.applications or "👋 Добро пожаловать!"

            if settings.photo.startswith("AgAC"):  # Фото
                await bot.send_photo(
                    user_id,
                    photo=settings.photo,
                    caption=text
                )
            else:  # Видео
                await bot.send_video(
                    user_id,
                    video=settings.photo,
                    caption=text
                )
        else:
            # Только текст
            text = "👋 <b>Добро пожаловать!</b>\n\nВы успешно прошли проверку."
            await bot.send_message(user_id, text)

        logger.info(f"[id{user_id}] Приветствие после капчи отправлено")

    except Exception as e:
        logger.error(f"[id{user_id}] Ошибка отправки приветствия: {e}")