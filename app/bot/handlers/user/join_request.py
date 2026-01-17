import asyncio
from aiogram import Router
from aiogram.types import ChatJoinRequest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.core import get_logger, get_config
from app.database import get_session, crud

logger = get_logger(__name__)
router = Router()


@router.chat_join_request()
async def handle_join_request(update: ChatJoinRequest) -> None:
    """
    Обработка новой заявки на вступление.

    Последовательность по ТЗ:
    1. Отправить приветственное сообщение
    2. Отправить капчу (через 5 секунд после приветствия)
    3. После прохождения капчи:
       - Если автоприём ВКЛ → одобрить заявку
       - Если автоприём ВЫКЛ → добавить в очередь
    """
    config = get_config()
    user = update.from_user

    logger.info(f"[id{user.id}] Новая заявка от @{user.username or 'NoUsername'}")

    # Проверяем, не забанен ли пользователь
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

    # Регистрируем пользователя в БД
    async for session in get_session():
        existing_user = await crud.get_user_by_chat_id(session, user.id)
        if not existing_user:
            await crud.create_user(session, user.id, user.username)
            logger.info(f"[id{user.id}] Пользователь зарегистрирован")

    # ШАГ 1: Отправляем приветственное сообщение СРАЗУ
    welcome_sent = await send_welcome(update)

    if not welcome_sent:
        logger.error(f"[id{user.id}] Не удалось отправить приветствие, отклоняем заявку")
        try:
            await update.decline()
        except TelegramBadRequest:
            pass
        return

    # ШАГ 2: Ждём 5 секунд и отправляем капчу
    await asyncio.sleep(5)

    if config.captcha_enabled:
        captcha_sent = await send_captcha(update)

        if not captcha_sent:
            logger.error(f"[id{user.id}] Не удалось отправить капчу, отклоняем заявку")
            try:
                await update.decline()
            except TelegramBadRequest:
                pass
            return

        logger.info(f"[id{user.id}] Ожидаем прохождения капчи...")

        # ШАГ 3 будет в обработчике капчи (captcha.py)
        # После прохождения капчи проверим автоприём

    else:
        # Если капча выключена, сразу обрабатываем заявку
        await process_after_captcha(update)


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
            except:
                pass

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


async def send_captcha(update: ChatJoinRequest) -> bool:
    """
    Отправить капчу пользователю.

    По ТЗ: картинка + текст согласия + 4 варианта смайликов

    Returns:
        True если капча отправлена успешно
    """
    from app.bot.keyboards import get_captcha_keyboard
    from app.bot.states import CaptchaStates
    from aiogram.fsm.context import FSMContext

    # Варианты капчи (пока хардкод, потом из БД)
    variants = ["🔑", "🥺", "👱🏾‍♀️", "🤖"]
    correct_answer = "👱🏾‍♀️"

    try:
        # Сохраняем правильный ответ в Redis для проверки
        from redis.asyncio import Redis
        from app.core import get_config
        config = get_config()

        try:
            redis = Redis.from_url(config.redis_url, decode_responses=True)
            # Сохраняем на 5 минут (timeout капчи)
            await redis.setex(f"captcha:{update.from_user.id}", 300, correct_answer)
            await redis.setex(f"captcha_attempts:{update.from_user.id}", 300, "0")
            await redis.close()
        except:
            logger.warning(f"[id{update.from_user.id}] Redis недоступен, используем in-memory")

        # Отправляем капчу
        config = get_config()
        captcha_image = config.captcha_image_path

        # Текст под капчей
        caption_text = (
            "🔐 <b>Проверка безопасности</b>\n\n"
            "Выберите правильный смайлик:\n\n"
            "<i>⚠️ При ответе вы соглашаетесь на отправку вам сообщений</i>"
        )

        try:
            # Пытаемся отправить с картинкой
            from aiogram.types import FSInputFile
            await update.bot.send_photo(
                update.from_user.id,
                photo=FSInputFile(captcha_image),
                caption=caption_text,
                reply_markup=get_captcha_keyboard(variants)
            )
        except:
            # Если картинки нет, отправляем просто текст
            await update.bot.send_message(
                update.from_user.id,
                caption_text,
                reply_markup=get_captcha_keyboard(variants)
            )

        logger.info(f"[id{update.from_user.id}] Капча отправлена")
        return True

    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.error(f"[id{update.from_user.id}] Не удалось отправить капчу: {e}")
        return False


async def process_after_captcha(update: ChatJoinRequest, auto_accept: bool | None = None) -> None:
    """
    Обработка после прохождения капчи.

    Args:
        update: Заявка на вступление
        auto_accept: Принудительное значение автоприёма (если None - берём из настроек)
    """
    from app.database import get_session, crud
    from app.core import get_config

    config = get_config()

    # Определяем автоприём
    if auto_accept is None:
        auto_accept = config.auto_accept_default

        # Проверяем настройки из БД
        async for session in get_session():
            settings = await crud.get_admin_settings(session, settings_id=1)
            if settings and settings.applications is not None:
                auto_accept = bool(settings.applications)

    if auto_accept:
        # Автоприём включён → принимаем заявку
        try:
            await update.approve()
            logger.info(f"[id{update.from_user.id}] Заявка автоматически одобрена (капча пройдена)")
        except TelegramBadRequest as e:
            if "USER_ALREADY_PARTICIPANT" not in str(e):
                logger.error(f"[id{update.from_user.id}] Ошибка одобрения: {e}")
    else:
        # Автоприём выключен → добавляем в очередь
        async for session in get_session():
            # Проверяем, нет ли уже заявки
            existing = await crud.get_pending_requests(
                session,
                limit=1,
                offset=0
            )

            # Фильтруем по user_id вручную (так как нет метода get_by_user_id)
            already_exists = any(req.user_id == update.from_user.id for req in existing)

            if not already_exists:
                await crud.create_pending_request(
                    session,
                    user_id=update.from_user.id,
                    chat_id=update.chat.id,
                    username=update.from_user.username,
                    first_name=update.from_user.first_name
                )
                logger.info(f"[id{update.from_user.id}] Добавлен в очередь (капча пройдена)")
            else:
                logger.info(f"[id{update.from_user.id}] Уже в очереди")