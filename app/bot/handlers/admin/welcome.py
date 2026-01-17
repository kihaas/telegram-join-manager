import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from raito.plugins.roles import DEVELOPER, OWNER, ADMINISTRATOR

from app.core import get_logger
from app.database import get_session, crud
from app.bot.states import WelcomeStates
from app.bot.keyboards import get_back_to_menu

logger = get_logger(__name__)
router = Router()


@router.message(F.text == "✉️ Приветствие", DEVELOPER | OWNER | ADMINISTRATOR)
@router.callback_query(F.data == "admin:welcome", DEVELOPER | OWNER | ADMINISTRATOR)
async def welcome_menu(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Меню управления приветствием.

    По ТЗ:
    - Показать текущее приветствие
    - Кнопка "Изменить приветствие"
    """
    await state.clear()

    # Получаем текущее приветствие
    async for session in get_session():
        settings = await crud.get_admin_settings(session, settings_id=2)

    if settings and settings.applications:
        current_text = settings.applications
        has_photo = bool(settings.photo)
    else:
        current_text = "Не настроено"
        has_photo = False

    # Показываем превью
    text = (
        "✉️ <b>Управление приветствием</b>\n\n"
        "<b>Текущее приветствие:</b>\n"
        f"{current_text[:200]}{'...' if len(current_text) > 200 else ''}\n\n"
        f"📎 Медиа: {'✅ Да' if has_photo else '❌ Нет'}"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить приветствие", callback_data="welcome:edit")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:menu")]
    ])

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()


@router.callback_query(F.data == "welcome:edit", DEVELOPER | OWNER | ADMINISTRATOR)
async def start_edit_welcome(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать редактирование приветствия."""

    instruction = (
        "✏️ <b>Редактирование приветствия</b>\n\n"
        "Отправьте новый текст (HTML формат) с фото/видео или просто текст.\n\n"
        "<b>Персонализация:</b>\n"
        "├ <code>{name}</code> — имя пользователя\n\n"
        "<b>Добавление кнопок:</b>\n"
        "Чтобы добавить кнопки, в конце сообщения укажите их согласно формату.\n"
        "Чтобы отправить несколько кнопок за 1 раз, используйте разделитель «|».\n"
        "Каждый новый ряд – с новой строчки.\n\n"
        "<code>Текст кнопки - URL ссылка</code>\n\n"
        "<b>Пример:</b>\n"
        "<code>Google - google.com</code>\n"
        "<code>Google - google.com | Yahoo - yahoo.com</code>\n"
        "<code>Bing - bing.com | Yandex - yandex.com</code>"
    )

    await callback.message.edit_text(instruction, reply_markup=get_back_to_menu())
    await state.set_state(WelcomeStates.waiting_content)
    await callback.answer()


@router.message(WelcomeStates.waiting_content, DEVELOPER | OWNER | ADMINISTRATOR)
async def process_welcome_content(message: Message, state: FSMContext) -> None:
    """Обработка нового приветствия."""

    # Получаем текст и медиа
    text = message.html_text or message.caption
    photo_id = None

    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.video:
        photo_id = message.video.file_id

    if not text:
        await message.answer("⚠️ Сообщение должно содержать текст!")
        return

    # Парсим кнопки
    buttons_json = "[]"
    clean_text = text

    from app.bot.keyboards import parse_buttons_from_text
    markup = parse_buttons_from_text(text)

    if markup:
        # Есть кнопки - извлекаем их
        import re
        pattern = re.compile(r'(.+?)\s*-\s*(https?://\S+|[a-zA-Z0-9.-]+\.[a-z]{2,})')

        buttons = []
        lines = text.split('\n')
        clean_lines = []

        for line in lines:
            matches = pattern.findall(line)
            if matches:
                # Это строка с кнопками
                row = [{"text": m[0].strip(), "url": m[1].strip()} for m in matches]
                buttons.append(row)
            else:
                # Обычная строка текста
                clean_lines.append(line)

        clean_text = '\n'.join(clean_lines).strip()
        buttons_json = json.dumps(buttons, ensure_ascii=False)

    # Сохраняем в БД
    async for session in get_session():
        await crud.update_admin_settings(
            session,
            settings_id=2,
            applications=clean_text,
            photo=photo_id,
            buttons=buttons_json
        )

    logger.info(f"[id{message.from_user.id}] Обновил приветствие")

    # Показываем превью
    preview_text = (
        "✅ <b>Приветствие обновлено!</b>\n\n"
        "<b>Превью:</b>\n"
        f"{clean_text}\n\n"
    )

    if photo_id:
        preview_text += "📎 Медиа: прикреплено\n"

    if buttons:
        preview_text += f"🔘 Кнопок: {sum(len(row) for row in buttons)}\n"

    await message.answer(preview_text, reply_markup=markup)

    await state.clear()

    # Возврат в меню
    await message.answer(
        "Выберите раздел:",
        reply_markup=get_back_to_menu()
    )