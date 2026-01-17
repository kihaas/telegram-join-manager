"""Сервис капчи - генерация и отправка."""

import os
import random
from pathlib import Path
from typing import Tuple, List

from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from app.core import get_logger, get_config

logger = get_logger(__name__)

# Путь к капчам
CAPTCHA_BASE_PATH = Path(os.getenv("CAPTCHA_IMAGE_PATH", "assets/"))

# 3 фиксированных варианта капчи
CAPTCHA_VARIANTS = [
    (CAPTCHA_BASE_PATH / "smile_1.png", "😄", ["😄", "😎", "⭐", "🤖"]),
    (CAPTCHA_BASE_PATH / "smile_2.png", "😎", ["😄", "😎", "⭐", "🤖"]),
    (CAPTCHA_BASE_PATH / "smile_3.png", "⭐", ["😄", "😎", "⭐", "🤖"]),
]


def get_random_captcha() -> Tuple[Path, str, List[str]]:
    """
    Получить случайный вариант капчи из 3 фиксированных.

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


async def send_captcha_to_user(bot, user_id: int) -> bool:
    """
    Отправить капчу пользователю.

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя

    Returns:
        True если капча отправлена успешно
    """
    try:
        # Получаем случайную капчу
        image_path, correct_answer, variants = get_random_captcha()

        # Проверяем существование файла
        if not image_path.exists():
            logger.error(f"Файл капчи не найден: {image_path}")
            # Пытаемся отправить без картинки
            image_path = None

        # Сохраняем правильный ответ в Redis
        config = get_config()
        try:
            redis = Redis.from_url(config.redis_url, decode_responses=True)
            # Сохраняем на 5 минут (300 секунд) по ТЗ
            await redis.setex(f"captcha:{user_id}", 300, correct_answer)
            # Сбрасываем счётчик попыток
            await redis.setex(f"captcha_attempts:{user_id}", 300, "0")
            await redis.close()
        except Exception as e:
            logger.warning(f"[id{user_id}] Redis недоступен: {e}")

        # Создаём клавиатуру
        keyboard = build_captcha_keyboard(variants, user_id, correct_answer)

        # Текст капчи
        caption = (
            "🔐 <b>Проверка безопасности</b>\n\n"
            "Выберите эмодзи, которое изображено на картинке:\n\n"
            "⚠️ У вас есть <b>3 попытки</b>\n"
            "⚠️ <i>При ответе вы соглашаетесь на получение сообщений от бота</i>"
        )

        # Отправляем капчу
        if image_path:
            photo = FSInputFile(image_path)
            await bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=caption,
                reply_markup=keyboard
            )
        else:
            # Без картинки
            await bot.send_message(
                chat_id=user_id,
                text=caption,
                reply_markup=keyboard
            )

        logger.info(f"[id{user_id}] Капча отправлена: {correct_answer}")
        return True

    except Exception as e:
        logger.error(f"[id{user_id}] Ошибка отправки капчи: {e}")
        return False