from aiogram import Router
from aiogram.types import ChatJoinRequest
from aiogram.exceptions import TelegramBadRequest

from app.core import get_logger, get_config
from app.database import get_session, crud
from app.services.captcha import send_captcha_to_user

logger = get_logger(__name__)
router = Router(name="join_request_router")


@router.chat_join_request()
async def handle_join_request(update: ChatJoinRequest) -> None:
    """Обработка новой заявки на вступление."""
    config = get_config()
    user = update.from_user

    logger.info(f"[id{user.id}] Новая заявка от @{user.username or 'NoUsername'}")

    # Проверяем, не забанен ли пользователь
    try:
        from raito import Raito
        raito: Raito = update.bot.get("raito")
        user_role = await raito.role_manager.get_role(update.bot.id, user.id)

        if user_role == "tester":
            logger.info(f"[id{user.id}] Пользователь забанен, заявка отклонена")
            try:
                await update.decline()
            except TelegramBadRequest:
                pass
            return
    except (KeyError, AttributeError) as e:
        logger.warning(f"[id{user.id}] Raito не инициализирован: {e}")

    # Регистрируем пользователя в БД
    async for session in get_session():
        existing_user = await crud.get_user_by_chat_id(session, user.id)
        if not existing_user:
            await crud.create_user(session, user.id, user.username)
            logger.info(f"[id{user.id}] Пользователь зарегистрирован")

    # Проверяем настройки автоприёма
    auto_accept = config.auto_accept_default

    async for session in get_session():
        settings = await crud.get_admin_settings(session, settings_id=1)
        if settings and settings.applications is not None:
            auto_accept = bool(settings.applications)

    # Если автоприём включён
    if auto_accept:
        try:
            await update.approve()
            logger.info(f"[id{user.id}] Заявка автоматически одобрена")

            # Отправляем капчу, если включена
            if config.captcha_enabled:
                await send_captcha_to_user(update.bot, user.id)
            else:
                # Сразу отправляем приветствие
                await send_welcome(update)

        except TelegramBadRequest as e:
            if "USER_ALREADY_PARTICIPANT" not in str(e):
                logger.error(f"[id{user.id}] Ошибка одобрения заявки: {e}")

    else:
        # Сохраняем заявку для ручной обработки
        async for session in get_session():
            await crud.create_pending_request(
                session,
                user_id=user.id,
                chat_id=update.chat.id,
                username=user.username,
                first_name=user.first_name
            )

        logger.info(f"[id{user.id}] Заявка сохранена для ручной обработки")

        # TODO: Уведомление админов (если включено)


async def send_welcome(update: ChatJoinRequest) -> None:
    """Отправить приветственное сообщение (без капчи)."""
    from app.database import get_session, crud

    try:
        # Получаем настройки приветствия из БД (id=2 для контента)
        async for session in get_session():
            settings = await crud.get_admin_settings(session, settings_id=2)

        if settings and settings.applications:
            text = settings.applications
            # Персонализация
            if "{name}" in text:
                text = text.replace("{name}", update.from_user.first_name or "друг")
        else:
            text = f"👋 Привет, {update.from_user.first_name}!\n\nДобро пожаловать в группу!"

        # Отправляем сообщение
        if settings and settings.photo:
            # С медиа
            if settings.photo.startswith("AgAC"):
                await update.bot.send_photo(
                    update.from_user.id,
                    photo=settings.photo,
                    caption=text
                )
            else:
                await update.bot.send_video(
                    update.from_user.id,
                    video=settings.photo,
                    caption=text
                )
        else:
            # Только текст
            await update.bot.send_message(
                update.from_user.id,
                text
            )

        logger.info(f"[id{update.from_user.id}] Приветствие отправлено")

    except TelegramBadRequest as e:
        logger.error(f"[id{update.from_user.id}] Не удалось отправить приветствие: {e}")
    except Exception as e:
        logger.error(f"[id{update.from_user.id}] Неожиданная ошибка: {e}")