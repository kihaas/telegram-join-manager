from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_admin_reply_menu() -> ReplyKeyboardMarkup:
    """Reply-клавиатура админ-меню (основная)."""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="📩 Рассылка")
    )
    builder.row(
        KeyboardButton(text="✉️ Приветствие"),
        KeyboardButton(text="📋 Заявки")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки")
    )

    return builder.as_markup(resize_keyboard=True)


def get_captcha_keyboard(variants: list[str]) -> ReplyKeyboardMarkup:
    """
    Клавиатура для капчи (смайлики или варианты ответов).

    Args:
        variants: Список вариантов (например, ["🔑", "🥺", "👱🏾‍♀️", "🤖"])
    """
    builder = ReplyKeyboardBuilder()

    # Располагаем кнопки в 2 ряда по 2
    for i in range(0, len(variants), 2):
        row_variants = variants[i:i + 2]
        builder.row(*[KeyboardButton(text=variant) for variant in row_variants])

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def remove_keyboard() -> ReplyKeyboardMarkup:
    """Удаление клавиатуры."""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()