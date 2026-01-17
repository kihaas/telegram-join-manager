"""Обработчики рассылки сообщений."""
import asyncio
import json
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from raito.plugins.roles import DEVELOPER, OWNER, ADMINISTRATOR

from app.core import get_logger
from app.bot.states import BroadcastStates
from app.bot.keyboards import get_back_to_menu, parse_buttons_from_text
from app.services.broadcast_service import send_broadcast

logger = get_logger(__name__)
router = Router()


@router.message(F.text == "📩 Рассылка", DEVELOPER | OWNER | ADMINISTRATOR)
@router.callback_query(F.data == "admin:broadcast", DEVELOPER | OWNER | ADMINISTRATOR)
async def broadcast_menu(event: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Меню рассылки.
    """
    await state.clear()

    text = (
        "📩 <b>Рассылка сообщений</b>\n\n"
        "Выберите действие:\n"
        "├ ✏️ <b>Создать рассылку</b> - отправить новое сообщение\n"
        "├ ⏸️ <b>Текущая рассылка</b> - управление активной рассылкой\n"
        "└ 📊 <b>Статистика</b> - просмотр результатов\n\n"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Создать рассылку", callback_data="broadcast:create")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin:menu")]
    ])

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text, reply_markup=keyboard)
        await event.answer()


@router.callback_query(F.data == "broadcast:create", DEVELOPER | OWNER | ADMINISTRATOR)
async def start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать создание рассылки."""

    instruction = (
        "✏️ <b>Создание рассылки</b>\n\n"
        "Отправьте сообщение (текст + фото/видео), которое хотите разослать.\n\n"
        "<b>Персонализация:</b>\n"
        "├ <code>{name}</code> — имя пользователя\n"
        "├ <code>{username}</code> — username (если есть)\n\n"
        "<b>Добавление ссылок:</b>\n"
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
    await state.set_state(BroadcastStates.waiting_content)
    await callback.answer()


@router.message(BroadcastStates.waiting_content, F.text | F.photo | F.video, DEVELOPER | OWNER | ADMINISTRATOR)
async def process_broadcast_content(message: Message, state: FSMContext) -> None:
    """Обработка контента рассылки."""
    # Получаем текст и медиа
    text = message.text or message.caption
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
    buttons = []
    markup = None

    pattern = re.compile(r'(.+?)\s*-\s*(https?://\S+|[a-zA-Z0-9.-]+\.[a-z]{2,})')

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

    if buttons:
        clean_text = '\n'.join(clean_lines).strip()
        buttons_json = json.dumps(buttons, ensure_ascii=False)
        markup = parse_buttons_from_text(text)

    # Сохраняем в состояние
    await state.update_data({
        'text': clean_text,
        'photo_id': photo_id,
        'buttons': buttons_json,
        'markup': markup
    })

    # Показываем предпросмотр
    preview_text = (
        "👁 <b>Предпросмотр рассылки</b>\n\n"
        "<b>Сообщение:</b>\n"
        f"{clean_text}\n\n"
    )

    if photo_id:
        preview_text += "📎 Медиа: прикреплено\n"

    if buttons:
        preview_text += f"🔘 Кнопок: {sum(len(row) for row in buttons)}\n"

    preview_text += "\n<b>Отправить рассылку?</b>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:send"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="broadcast:edit")
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin:broadcast")]
    ])

    # Отправляем предпросмотр
    if photo_id:
        if photo_id.startswith("AgAC"):
            await message.answer_photo(
                photo_id,
                caption=preview_text,
                reply_markup=keyboard
            )
        else:
            await message.answer_video(
                photo_id,
                caption=preview_text,
                reply_markup=keyboard
            )
    else:
        await message.answer(preview_text, reply_markup=keyboard)

    await state.set_state(BroadcastStates.preview)


@router.callback_query(F.data == "broadcast:send", DEVELOPER | OWNER | ADMINISTRATOR)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение и запуск рассылки."""
    data = await state.get_data()

    if not data:
        await callback.answer("⚠️ Данные рассылки не найдены")
        return

    text = data.get('text', '')
    photo_id = data.get('photo_id')
    buttons = data.get('buttons', '[]')
    markup = data.get('markup')

    # Получаем количество пользователей
    from app.database import get_session, crud

    async for session in get_session():
        total_users = await crud.get_users_count(session)

    # Показываем подтверждение
    confirm_text = (
        "🚀 <b>Запуск рассылки</b>\n\n"
        f"📊 <b>Количество получателей:</b> <code>{total_users}</code>\n"
        f"📝 <b>Длина сообщения:</b> <code>{len(text)}</code> символов\n\n"
        "⚠️ <i>Рассылка будет отправлена всем пользователям из базы данных.</i>\n"
        "⏳ <i>Это может занять некоторое время...</i>\n\n"
        "<b>Запустить рассылку?</b>"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Запустить", callback_data="broadcast:confirm_send"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast:cancel")
        ]
    ])

    await callback.message.edit_text(confirm_text, reply_markup=keyboard)
    await state.set_state(BroadcastStates.confirm)
    await callback.answer()


@router.callback_query(F.data == "broadcast:confirm_send", DEVELOPER | OWNER | ADMINISTRATOR)
async def start_broadcast_send(callback: CallbackQuery, state: FSMContext) -> None:
    """Запуск рассылки."""
    data = await state.get_data()

    if not data:
        await callback.answer("⚠️ Данные рассылки не найдены")
        return

    text = data.get('text', '')
    photo_id = data.get('photo_id')
    buttons = data.get('buttons', '[]')
    markup = data.get('markup')

    # Сообщение о начале
    start_text = (
        "⏳ <b>Рассылка запущена</b>\n\n"
        "Отправка сообщений началась...\n"
        "Это может занять некоторое время.\n\n"
        "<i>Вы будете уведомлены по завершении.</i>"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛔ Остановить", callback_data="broadcast:stop")]
    ])

    await callback.message.edit_text(start_text, reply_markup=keyboard)

    # Запускаем рассылку в фоне
    asyncio.create_task(
        send_broadcast(
            bot=callback.bot,
            user_id=callback.from_user.id,
            text=text,
            photo_id=photo_id,
            markup=markup,
            state=state
        )
    )

    await state.set_state(BroadcastStates.running)
    await callback.answer()


@router.callback_query(F.data == "broadcast:stop", DEVELOPER | OWNER | ADMINISTRATOR)
async def stop_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Остановка рассылки."""
    # Помечаем рассылку как отменённую
    await state.update_data({'broadcast_cancelled': True})

    await callback.message.edit_text(
        "🛑 <b>Рассылка остановлена</b>\n\n"
        "Рассылка была прервана.\n"
        "Часть сообщений могла быть отправлена.",
        reply_markup=get_back_to_menu()
    )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "broadcast:edit", DEVELOPER | OWNER | ADMINISTRATOR)
async def edit_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактирование рассылки."""
    instruction = (
        "✏️ <b>Редактирование рассылки</b>\n\n"
        "Отправьте новое сообщение (текст + фото/видео).\n\n"
        "Формат кнопок:\n"
        "<code>Текст - URL</code>\n"
        "<code>Текст1 - URL1 | Текст2 - URL2</code>"
    )

    await callback.message.edit_text(instruction, reply_markup=get_back_to_menu())
    await state.set_state(BroadcastStates.waiting_content)
    await callback.answer()


@router.callback_query(F.data == "broadcast:cancel", DEVELOPER | OWNER | ADMINISTRATOR)
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена создания рассылки."""
    await state.clear()
    await broadcast_menu(callback, state)
    await callback.answer()