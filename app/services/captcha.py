import os
import random
from pathlib import Path
from typing import List, Tuple, Optional

from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_logger, get_config
from app.database import crud, get_session
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

    return str(image_path), correct_emoji, shuffled_variants


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

        # Сохраняем правильный ответ в Redis
        from redis.asyncio import Redis
        config = get_config()
        redis = Redis.from_url(config.redis_url, decode_responses=True)

        # Сохраняем на 5 минут (300 секунд) как по ТЗ
        await redis.setex(f"captcha:{user_id}", 300, correct_answer)
        # Сбрасываем счётчик попыток
        await redis.setex(f"captcha_attempts:{user_id}", 300, "0")
        await redis.close()

        # Создаём клавиатуру
        keyboard = build_captcha_keyboard(variants, user_id, correct_answer)

        # Отправляем картинку с капчей
        photo = FSInputFile(image_path)

        caption = (
            "🔐 <b>Проверка безопасности</b>\n\n"
            "Выберите эмодзи, которое изображено на картинке:\n\n"
            "⚠️ У вас есть <b>3 попытки</b>\n"
            "После 3 неудачных попыток - бан на 5 минут"
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

    if attempts >= 3:  # По ТЗ: после 3 неудач бан на 5 минут
        try:
            from redis.asyncio import Redis
            redis = Redis.from_url(config.redis_url, decode_responses=True)

            # Бан на 5 минут
            await redis.setex(f"captcha_ban:{user_id}", 300, "1")

            # Удаляем данные капчи
            await redis.delete(f"captcha:{user_id}")
            await redis.delete(f"captcha_attempts:{user_id}")
            await redis.close()

            await bot.send_message(
                user_id,
                "❌ <b>Превышено количество попыток</b>\n\n"
                "Вы не прошли проверку безопасности.\n"
                "⏳ Попробуйте снова через <b>5 минут</b>."
            )

            logger.warning(f"[id{user_id}] Капча не пройдена ({attempts} попыток), бан на 5 минут")

            # Записываем неудачу в БД
            async for session in get_session():
                from app.database.models import CaptchaType
                await crud.create_captcha_attempt(
                    session,
                    user_id=user_id,
                    chat_id=chat_id,
                    captcha_type=CaptchaType.IMAGE,
                    is_successful=False,
                    attempts_count=attempts
                )

        except Exception as e:
            logger.error(f"[id{user_id}] Ошибка обработки бана: {e}")

    else:
        # Даём ещё попытку
        await bot.send_message(
            user_id,
            f"❌ <b>Неправильно!</b>\n\n"
            f"Попробуйте ещё раз.\n"
            f"Попыток осталось: {3 - attempts}"
        )

        # Отправляем новую капчу
        await send_captcha_to_user(bot, user_id)


async def process_approved_captcha(bot, user_id: int, chat_id: int, session: AsyncSession) -> None:
    """
    Обработка после успешного прохождения капчи.

    Проверяем автоприём:
    - Если ВКЛ → принимаем в группу
    - Если ВЫКЛ → добавляем в очередь
    """
    from app.core import get_config

    config = get_config()

    # Определяем автоприём
    auto_accept = config.auto_accept_default

    settings = await crud.get_admin_settings(session, settings_id=1)
    if settings and settings.applications is not None:
        auto_accept = bool(settings.applications)

    if auto_accept:
        # Автоприём включён → принимаем в группу
        try:
            # Снимаем ограничения с пользователя в чате
            from aiogram.types import ChatPermissions
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )

            await bot.restrict_chat_member(chat_id, user_id, permissions)

            await bot.send_message(
                user_id,
                "🎉 <b>Добро пожаловать!</b>\n\n"
                "Ваша заявка одобрена автоматически."
            )

            logger.info(f"[id{user_id}] Заявка одобрена автоматически (капча пройдена)")

        except Exception as e:
            logger.error(f"[id{user_id}] Ошибка при автоприёме: {e}")
            await bot.send_message(
                user_id,
                "✅ Проверка пройдена! Администратор скоро рассмотрит вашу заявку."
            )

    else:
        # Автоприём выключен → добавляем в очередь
        from app.database import get_session

        # Проверяем, нет ли уже заявки
        requests = await crud.get_pending_requests(session)
        already_exists = any(req.user_id == user_id for req in requests)

        if not already_exists:
            # Создаём заявку
            from app.database import get_session
            async for inner_session in get_session():
                user_data = await bot.get_chat(user_id)
                await crud.create_pending_request(
                    inner_session,
                    user_id=user_id,
                    chat_id=chat_id,
                    username=user_data.username,
                    first_name=user_data.first_name
                )

                # Получаем позицию в очереди
                all_requests = await crud.get_pending_requests(inner_session)
                position = len(all_requests)

                await bot.send_message(
                    user_id,
                    "📋 <b>Заявка принята!</b>\n\n"
                    f"Вы в очереди на вступление.\n"
                    f"Позиция: <code>{position}</code>\n\n"
                    f"Администратор скоро рассмотрит вашу заявку."
                )

                logger.info(f"[id{user_id}] Добавлен в очередь (позиция {position})")
        else:
            await bot.send_message(
                user_id,
                "📋 Вы уже в очереди на вступление.\n\n"
                "Администратор скоро рассмотрит вашу заявку."
            )

            logger.info(f"[id{user_id}] Уже в очереди")


async def handle_captcha_callback(bot, callback_data: str, user_id: int) -> bool:
    """
    Обработать callback от inline-кнопки капчи.

    Returns:
        True если капча пройдена, False если нет
    """
    try:
        # Парсим callback_data: captcha:user_id:emoji:правильный_ответ
        parts = callback_data.split(":")
        if len(parts) != 4:
            return False

        target_user_id = int(parts[1])
        user_answer = parts[2]
        correct_answer = parts[3]

        # Проверяем, что ответ соответствует пользователю
        if target_user_id != user_id:
            return False

        # Получаем попытки из Redis
        from redis.asyncio import Redis
        from app.core import get_config

        config = get_config()
        redis = Redis.from_url(config.redis_url, decode_responses=True)

        attempts_str = await redis.get(f"captcha_attempts:{user_id}")
        attempts = int(attempts_str) if attempts_str else 1

        # Проверяем ответ
        if user_answer == correct_answer:
            # ✅ Правильный ответ
            await redis.delete(f"captcha:{user_id}")
            await redis.delete(f"captcha_attempts:{user_id}")
            await redis.close()

            # Записываем успех в БД
            from app.database import get_session
            async for session in get_session():
                from app.database.models import CaptchaType
                await crud.create_captcha_attempt(
                    session,
                    user_id=user_id,
                    chat_id=user_id,  # Временно, нужно передать chat_id
                    captcha_type=CaptchaType.IMAGE,
                    is_successful=True,
                    attempts_count=attempts
                )

                # Обрабатываем заявку
                await process_approved_captcha(bot, user_id, user_id, session)

            await bot.send_message(
                user_id,
                "✅ <b>Проверка пройдена успешно!</b>",
                reply_markup=None
            )

            logger.info(f"[id{user_id}] Капча пройдена успешно")
            return True

        else:
            # ❌ Неправильный ответ
            attempts += 1
            await redis.setex(f"captcha_attempts:{user_id}", 300, str(attempts))
            await redis.close()

            if attempts >= 3:
                # 3 неудачи → бан на 5 минут
                await handle_captcha_failure(bot, user_id, user_id, attempts)
            else:
                # Даём ещё попытку
                await bot.send_message(
                    user_id,
                    f"❌ Неправильно! Попыток осталось: <b>{3 - attempts}</b>\n\n"
                    "Попробуйте ещё раз:"
                )

                # Отправляем новую капчу
                await send_captcha_to_user(bot, user_id)

            return False

    except Exception as e:
        logger.error(f"[id{user_id}] Ошибка обработки callback капчи: {e}")
        return False