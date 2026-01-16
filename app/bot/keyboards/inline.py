from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_main_menu() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        InlineKeyboardButton(text="📩 Рассылка", callback_data="admin:broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="✉️ Приветствие", callback_data="admin:welcome"),
        InlineKeyboardButton(text="📋 Заявки", callback_data="admin:requests")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings")
    )

    return builder.as_markup()


def get_back_to_menu() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:menu")]
    ])


def get_settings_menu(auto_accept: bool, captcha_enabled: bool) -> InlineKeyboardMarkup:
    """Меню настроек."""
    builder = InlineKeyboardBuilder()

    auto_accept_text = "✅ Автоприём ВКЛ" if auto_accept else "❌ Автоприём ВЫКЛ"
    captcha_text = "✅ Капча ВКЛ" if captcha_enabled else "❌ Капча ВЫКЛ"

    builder.row(
        InlineKeyboardButton(text=auto_accept_text, callback_data="settings:toggle_auto_accept")
    )
    builder.row(
        InlineKeyboardButton(text=captcha_text, callback_data="settings:toggle_captcha")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu")
    )

    return builder.as_markup()


def get_broadcast_controls(draft_id: int) -> InlineKeyboardMarkup:
    """Управление рассылкой."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"broadcast:edit:{draft_id}"),
        InlineKeyboardButton(text="🧪 Тест", callback_data=f"broadcast:test:{draft_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Запустить", callback_data=f"broadcast:send:{draft_id}"),
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"broadcast:delete:{draft_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:broadcast")
    )

    return builder.as_markup()


def get_broadcast_cancel() -> InlineKeyboardMarkup:
    """Кнопка отмены рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛔ Остановить рассылку", callback_data="broadcast:cancel")]
    ])


def get_confirm_buttons(action: str, data: str = "") -> InlineKeyboardMarkup:
    """Кнопки подтверждения действия."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{data}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel:{action}")
    )

    return builder.as_markup()


def get_add_buttons_keyboard() -> InlineKeyboardMarkup:
    """Предложение добавить кнопки."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Добавить кнопки", callback_data="buttons:add"),
        InlineKeyboardButton(text="➡️ Продолжить без кнопок", callback_data="buttons:skip")
    )

    return builder.as_markup()


def get_request_controls(request_id: int) -> InlineKeyboardMarkup:
    """Управление одной заявкой."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"request:approve:{request_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"request:decline:{request_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Отклонить + бан", callback_data=f"request:ban:{request_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К списку", callback_data="admin:requests")
    )

    return builder.as_markup()


def get_requests_pagination(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Пагинация для списка заявок."""
    builder = InlineKeyboardBuilder()

    buttons = []

    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"requests:page:{current_page - 1}"))

    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="requests:current"))

    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"requests:page:{current_page + 1}"))

    if buttons:
        builder.row(*buttons)

    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="requests:refresh"),
        InlineKeyboardButton(text="⚙️ Фильтры", callback_data="requests:filters")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:menu")
    )

    return builder.as_markup()


def get_requests_filters() -> InlineKeyboardMarkup:
    """Фильтры для заявок."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🆕 Новые", callback_data="requests:filter:new"),
        InlineKeyboardButton(text="⏰ Старые", callback_data="requests:filter:old")
    )
    builder.row(
        InlineKeyboardButton(text="📅 За сутки", callback_data="requests:filter:day"),
        InlineKeyboardButton(text="📆 За неделю", callback_data="requests:filter:week")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:requests")
    )

    return builder.as_markup()


def get_welcome_agree() -> InlineKeyboardMarkup:
    """Кнопка согласия с правилами."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я прочитал(а) правила", callback_data="welcome:agree")]
    ])


def parse_buttons_from_text(text: str) -> InlineKeyboardMarkup | None:
    """
    Парсинг кнопок из текста.

    Формат:
    Текст1 - URL1 | Текст2 - URL2
    Текст3 - URL3

    Returns:
        InlineKeyboardMarkup или None если кнопок нет
    """
    import re

    buttons = []
    pattern = re.compile(r'(.+?)\s*-\s*(https?://\S+)')

    for line in text.strip().split('\n'):
        row = []
        for match in pattern.finditer(line):
            button_text, url = match.groups()
            row.append(InlineKeyboardButton(text=button_text.strip(), url=url.strip()))

        if row:
            buttons.append(row)

    if not buttons:
        return None

    return InlineKeyboardMarkup(inline_keyboard=buttons)