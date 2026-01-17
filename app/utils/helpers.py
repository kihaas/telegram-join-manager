"""Вспомогательные функции."""

from datetime import datetime
from typing import Optional


def time_ago(dt: datetime) -> str:
    """
    Преобразовать datetime в человекочитаемый формат "N минут назад".

    Args:
        dt: Дата и время

    Returns:
        Строка вида "5 минут назад", "2 часа назад", "3 дня назад"
    """
    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)} сек назад"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} мин назад"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} ч назад"
    else:
        days = int(seconds / 86400)
        return f"{days} дн назад"


def format_time_in_queue(dt: datetime) -> str:
    """
    Форматировать время в очереди.

    Args:
        dt: Время подачи заявки

    Returns:
        Строка вида "в очереди 3 часа 12 минут"
    """
    now = datetime.utcnow()
    diff = now - dt

    total_seconds = int(diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"в очереди {hours} ч {minutes} мин"
    elif minutes > 0:
        return f"в очереди {minutes} мин"
    else:
        return "только что"


def validate_url(url: str) -> bool:
    """
    Проверить корректность URL.

    Args:
        url: Ссылка

    Returns:
        True если URL валидный
    """
    import re
    pattern = re.compile(
        r'^https?://'  # http:// или https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # домен...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...или IP
        r'(?::\d+)?'  # опциональный порт
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return pattern.match(url) is not None


def escape_html(text: str) -> str:
    """
    Экранировать HTML символы.

    Args:
        text: Текст

    Returns:
        Экранированный текст
    """
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезать текст до max_length символов.

    Args:
        text: Текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста

    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix