"""Обработка заявок на вступление в группу."""

import asyncio
from aiogram import Router
from aiogram.types import ChatJoinRequest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from raito import Raito

from app.core import get_logger, get_config
from app.database import get_session, crud
from app.services.captcha import send_captcha_to_user

logger = get_logger(__name__)
router = Router(name="join_requests_router")


@router.chat_join_request()
async def handle_join_request(update: ChatJoinRequest, raito: Raito) -> None:
    """
    Обработка новой заявки на вступление.

    Последовательность по ТЗ:
    1. Отправить приветственное сообщение
    2. Ждать 3 секунды
    3. Отправить капчу (ВСЕГДА, капча обязательна)
    4. После прохождения капчи:
       - Если автоприём ВКЛ → одобрить заявку
       - Если автоприём ВЫКЛ → добавить в очередь
    """
    config = get_config()
    user = update.from_user

    logger.info(f"[id{user.id}] Новая заявка от @{user.username or 'NoUsername'}")

    # Проверяем, не забанен ли пользователь
    user_role = await raito.role_manager.get_role(update.bot.id, user.id)

    if user_role == "tester":
        logger.info(f"[id{user.id}] Пользователь забанен, заявка отклонена")
        try:
            await update.decline()
        except TelegramBadRequest:
            pass
        return

    # Регистрируем пользователя в БД
    async for session in get_session():
        existing_user = await crud.get_user_by_chat_id(session, user.id)
        if not existing_user:
            await crud.create_user(session, user.id, user.username)
            logger.info(f"[id{user.id}] Пользователь зарегистрирован")

    # ШАГ 1: Отправляем приветственное сообщение
    welcome_sent = await send_welcome(update)

    if not welcome_sent:
        logger.error(f"[id{user.id}] Не удалось отправить приветствие")
        # Всё равно пытаемся отправить капчу
        pass

    # ШАГ 2: Ждём 3 секунды
    await asyncio.sleep(3)

    # ШАГ 3: Отправляем капчу
    captcha_sent = await send_captcha_to_user(update.bot, user.id)

    if not captcha_sent:
        logger.error(f"[id{user.id}] Не удалось отправить капчу, отклоняем заявку")
        try:
            await update.decline()
        except TelegramBadRequest:
            pass
        return

    logger.info(f"[id{user.id}] Ожидаем прохождения капчи...")

    # ШАГ 4 будет в обработчике капчи (captcha.py)
    # После прохождения капчи проверим автоприём


async def send_welcome(update: ChatJoinRequest) -> bool:
    """
    Отправить приветственное сообщение.

    Returns:
        True если сообщение отправлено успешно
    """
    from app.database import get_session, crud

    try:
        # Получаем настройки приветствия из БД (id=2 для контента)
        text = None
        photo = None
        buttons = None

        async for session in get_session():
            settings = await crud.get_admin_settings(session, settings_id=2)
            if settings:
                text = settings.applications  # Текст в поле applications
                photo = settings.photo
                buttons = settings.buttons

        # Дефолтное приветствие если не настроено
        if not text:
            text = (
                f"👋 Привет, {update.from_user.first_name}!\n\n"
                "Для доступа к группе пройдите простую проверку."
            )
        else:
            # Персонализация {name}
            text = text.replace("{name}", update.from_user.first_name or "друг")

        # Парсим кнопки если есть
        markup = None
        if buttons and buttons != '[]':
            from app.bot.keyboards import parse_buttons_from_text
            import json
            try:
                buttons_list = json.loads(buttons)
                # Преобразуем в текстовый формат для парсинга
                buttons_text = ""
                for row in buttons_list:
                    row_text = " | ".join([f"{btn['text']} - {btn['url']}" for btn in row])
                    buttons_text += row_text + "\n"

                if buttons_text.strip():
                    markup = parse_buttons_from_text(buttons_text)
            except Exception as e:
                logger.warning(f"Ошибка парсинга кнопок: {e}")

        # Отправляем сообщение
        if photo:
            # С медиа
            if photo.startswith("AgAC"):
                await update.bot.send_photo(
                    update.from_user.id,
                    photo=photo,
                    caption=text,
                    reply_markup=markup
                )
            else:
                await update.bot.send_video(
                    update.from_user.id,
                    video=photo,
                    caption=text,
                    reply_markup=markup
                )
        else:
            # Только текст
            await update.bot.send_message(
                update.from_user.id,
                text,
                reply_markup=markup
            )

        logger.info(f"[id{update.from_user.id}] Приветствие отправлено")
        return True

    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.error(f"[id{update.from_user.id}] Не удалось отправить приветствие: {e}")
        return False