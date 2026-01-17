"""Управление заявками."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from raito import Raito
from raito.plugins.roles import DEVELOPER, OWNER, ADMINISTRATOR

from app.core import get_logger
from app.database import get_session, crud
from app.database.models import RequestStatus

logger = get_logger(__name__)
router = Router()


@router.message(F.text == "📋 Заявки", DEVELOPER | OWNER | ADMINISTRATOR)
@router.callback_query(F.data == "admin:requests", DEVELOPER | OWNER | ADMINISTRATOR)
async def requests_menu(event: Message | CallbackQuery) -> None:
    """
    Меню управления заявками.

    По ТЗ:
    - Показать статус автоприёма (ВКЛ/ВЫКЛ)
    - Если ВЫКЛ: показать кол-во в очереди + кнопки "Включить" и "Посмотреть заявки"
    - Если ВКЛ: кнопка "Выключить"
    """
    from app.database import get_session, crud
    from app.core import get_config

    config = get_config()

    # Получаем текущий статус автоприёма
    auto_accept = config.auto_accept_default

    async for session in get_session():
        settings = await crud.get_admin_settings(session, settings_id=1)
        if settings and settings.applications is not None:
            auto_accept = bool(settings.applications)

        # Количество в очереди
        pending_count = await crud.get_pending_count(session, status=RequestStatus.PENDING)

    # Формируем текст и клавиатуру
    if auto_accept:
        # Автоприём ВКЛ
        text = (
            "📋 <b>Управление заявками</b>\n\n"
            "Автоприём: <b>✅ Включён</b>\n\n"
            "Все пользователи автоматически принимаются после прохождения капчи."
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Выключить автоприём", callback_data="requests:toggle_auto")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:menu")]
        ])

    else:
        # Автоприём ВЫКЛ
        text = (
            "📋 <b>Управление заявками</b>\n\n"
            "Автоприём: <b>❌ Выключен</b>\n"
            f"📊 Людей в очереди: <code>{pending_count}</code>\n\n"
            "Пользователи добавляются в очередь после прохождения капчи."
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = [
            [InlineKeyboardButton(text="✅ Включить автоприём", callback_data="requests:toggle_auto")]
        ]

        # Кнопка "Посмотреть заявки" только если есть заявки
        if pending_count > 0:
            buttons.append([InlineKeyboardButton(text="👁 Посмотреть заявки", callback_data="requests:view:0")])

        buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:menu")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем или редактируем сообщение
    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()


@router.callback_query(F.data == "requests:toggle_auto", DEVELOPER | OWNER | ADMINISTRATOR)
async def toggle_auto_accept(callback: CallbackQuery) -> None:
    """Переключение автоприёма."""
    from app.database import get_session, crud
    from app.core import get_config

    config = get_config()

    # Получаем текущий статус
    auto_accept = config.auto_accept_default

    async for session in get_session():
        settings = await crud.get_admin_settings(session, settings_id=1)
        if settings and settings.applications is not None:
            auto_accept = bool(settings.applications)

        # Переключаем
        new_status = 0 if auto_accept else 1
        await crud.update_admin_settings(session, settings_id=1, applications=new_status)

    status_text = "включён" if new_status else "выключен"
    logger.info(f"[id{callback.from_user.id}] Автоприём {status_text}")

    await callback.answer(f"Автоприём {status_text}")

    # Обновляем меню
    await requests_menu(callback)


@router.callback_query(F.data.startswith("requests:view:"), DEVELOPER | OWNER | ADMINISTRATOR)
async def view_requests(callback: CallbackQuery) -> None:
    """
    Просмотр заявок по одной.

    Формат: requests:view:<index>
    """
    # Извлекаем индекс
    parts = callback.data.split(":")
    current_index = int(parts[2])

    # Получаем заявку
    async for session in get_session():
        requests_list = await crud.get_pending_requests(
            session,
            status=RequestStatus.PENDING,
            limit=1,
            offset=current_index
        )

        total_count = await crud.get_pending_count(session, status=RequestStatus.PENDING)

    if not requests_list:
        await callback.answer("⚠️ Заявок не найдено")
        await requests_menu(callback)
        return

    request = requests_list[0]

    # Вычисляем время в очереди
    from datetime import datetime
    time_in_queue = datetime.utcnow() - request.request_time
    hours = time_in_queue.seconds // 3600
    minutes = (time_in_queue.seconds % 3600) // 60

    # Формируем текст
    text = (
        f"📋 <b>Заявка #{current_index + 1} из {total_count}</b>\n\n"
        f"👤 ID: <code>{request.user_id}</code>\n"
        f"📝 Username: @{request.username or 'Нет'}\n"
        f"🏷 Имя: {request.first_name or 'Нет'}\n"
        f"⏰ В очереди: <b>{hours} ч {minutes} мин</b>\n"
        f"📅 Подана: {request.request_time.strftime('%d.%m.%Y %H:%M')}"
    )

    # Кнопки управления
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    buttons = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"requests:approve:{request.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"requests:decline:{request.id}")
        ],
        [InlineKeyboardButton(text="🚫 Отклонить + бан", callback_data=f"requests:ban:{request.id}")]
    ]

    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"requests:view:{current_index - 1}"))

    if current_index < total_count - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"requests:view:{current_index + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin:requests")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("requests:approve:"), DEVELOPER | OWNER | ADMINISTRATOR)
async def approve_request(callback: CallbackQuery) -> None:
    """Принять заявку."""
    request_id = int(callback.data.split(":")[2])

    async for session in get_session():
        request = await session.get(crud.PendingRequest, request_id)

        if not request:
            await callback.answer("⚠️ Заявка не найдена")
            return

        # Обновляем статус
        await crud.update_request_status(
            session,
            request_id,
            RequestStatus.APPROVED,
            processed_by=callback.from_user.id
        )

        # Одобряем заявку в Telegram
        try:
            # TODO: Нужен chat_join_request object для approve()
            # Пока просто уведомляем пользователя
            await callback.bot.send_message(
                request.user_id,
                "✅ <b>Ваша заявка одобрена!</b>\n\nДобро пожаловать в группу!"
            )

            logger.info(f"[id{callback.from_user.id}] Одобрил заявку от {request.user_id}")

        except TelegramBadRequest as e:
            logger.error(f"Ошибка одобрения заявки: {e}")

    await callback.answer("✅ Заявка одобрена")

    # Показываем следующую заявку
    await view_requests(callback)


@router.callback_query(F.data.startswith("requests:decline:"), DEVELOPER | OWNER | ADMINISTRATOR)
async def decline_request(callback: CallbackQuery) -> None:
    """Отклонить заявку."""
    request_id = int(callback.data.split(":")[2])

    async for session in get_session():
        request = await session.get(crud.PendingRequest, request_id)

        if not request:
            await callback.answer("⚠️ Заявка не найдена")
            return

        # Обновляем статус
        await crud.update_request_status(
            session,
            request_id,
            RequestStatus.DECLINED,
            processed_by=callback.from_user.id
        )

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                request.user_id,
                "❌ Ваша заявка отклонена."
            )

            logger.info(f"[id{callback.from_user.id}] Отклонил заявку от {request.user_id}")

        except TelegramBadRequest:
            pass

    await callback.answer("❌ Заявка отклонена")

    # Показываем следующую заявку
    await view_requests(callback)


@router.callback_query(F.data.startswith("requests:ban:"), DEVELOPER | OWNER | ADMINISTRATOR)
async def ban_request(callback: CallbackQuery, raito: Raito) -> None:
    """Отклонить заявку + бан."""
    request_id = int(callback.data.split(":")[2])

    async for session in get_session():
        request = await session.get(crud.PendingRequest, request_id)

        if not request:
            await callback.answer("⚠️ Заявка не найдена")
            return

        # Обновляем статус
        await crud.update_request_status(
            session,
            request_id,
            RequestStatus.BANNED,
            processed_by=callback.from_user.id
        )

        # Баним через Raito
        await raito.role_manager.assign_role(
            callback.bot.id,
            callback.from_user.id,
            request.user_id,
            "tester"
        )

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                request.user_id,
                "🚫 Ваша заявка отклонена. Вы заблокированы."
            )

            logger.info(f"[id{callback.from_user.id}] Забанил пользователя {request.user_id}")

        except TelegramBadRequest:
            pass

    await callback.answer("🚫 Пользователь забанен")

    # Показываем следующую заявку
    await view_requests(callback)