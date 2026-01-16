from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from raito.plugins.roles import DEVELOPER, OWNER, ADMINISTRATOR

from app.bot.keyboards import get_admin_main_menu, get_admin_reply_menu
from app.core import get_logger

logger = get_logger(__name__)
router = Router()


@router.message(Command("start"), DEVELOPER | OWNER | ADMINISTRATOR)
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Команда /start для админов."""
    await state.clear()

    await message.answer(
        "🤖 <b>Панель управления</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_main_menu()
    )

    # Также отправляем reply-клавиатуру
    await message.answer(
        "Меню:",
        reply_markup=get_admin_reply_menu()
    )


@router.callback_query(F.data == "admin:menu", DEVELOPER | OWNER | ADMINISTRATOR)
async def admin_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню."""
    await state.clear()

    await callback.message.edit_text(
        "🤖 <b>Панель управления</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_main_menu()
    )
    await callback.answer()


@router.message(F.text == "📊 Статистика", DEVELOPER | OWNER | ADMINISTRATOR)
@router.callback_query(F.data == "admin:stats", DEVELOPER | OWNER | ADMINISTRATOR)
async def show_statistics(event: Message | CallbackQuery) -> None:
    """Показать статистику."""
    from app.database import get_session, crud

    # Получаем статистику из БД
    async for session in get_session():
        total_users = await crud.get_users_count(session)
        new_today = await crud.get_new_users_count(session, days=1)
        new_week = await crud.get_new_users_count(session, days=7)
        new_month = await crud.get_new_users_count(session, days=30)

        pending_count = await crud.get_pending_count(session)
        captcha_success = await crud.get_captcha_success_rate(session)

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <code>{total_users}</code>\n"
        f"├ За сегодня: <code>{new_today}</code>\n"
        f"├ За неделю: <code>{new_week}</code>\n"
        f"└ За месяц: <code>{new_month}</code>\n\n"
        f"📋 В очереди: <code>{pending_count}</code>\n"
        f"✅ Капча пройдена: <code>{captcha_success:.1f}%</code>"
    )

    if isinstance(event, Message):
        await event.answer(text)
    else:
        await event.message.edit_text(text, reply_markup=get_admin_main_menu())
        await event.answer()


@router.message(Command("ban"), DEVELOPER | OWNER | ADMINISTRATOR)
async def cmd_ban(message: Message) -> None:
    """Забанить пользователя через raito."""
    from raito import Raito
    from aiogram import Bot

    # Парсим аргументы
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Использование: /ban <user_id>")
        return

    user_id = int(args[1])
    bot: Bot = message.bot
    raito: Raito = message.bot.get("raito")

    # Назначаем роль "tester" (забаненный)
    await raito.role_manager.assign_role(bot.id, message.from_user.id, user_id, "tester")

    await message.answer(f"✅ Пользователь <code>{user_id}</code> забанен")
    logger.info(f"[id{message.from_user.id}] Забанил пользователя {user_id}")


@router.message(Command("unban"), DEVELOPER | OWNER | ADMINISTRATOR)
async def cmd_unban(message: Message) -> None:
    """Разбанить пользователя."""
    from raito import Raito
    from aiogram import Bot

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Использование: /unban <user_id>")
        return

    user_id = int(args[1])
    bot: Bot = message.bot
    raito: Raito = message.bot.get("raito")

    # Убираем роль
    await raito.role_manager.revoke_role(bot.id, message.from_user.id, user_id)

    await message.answer(f"✅ Пользователь <code>{user_id}</code> разбанен")
    logger.info(f"[id{message.from_user.id}] Разбанил пользователя {user_id}")


@router.message(Command("banlist"), DEVELOPER | OWNER | ADMINISTRATOR)
async def cmd_banlist(message: Message) -> None:
    """Список забаненных пользователей."""
    from raito import Raito
    from aiogram import Bot

    bot: Bot = message.bot
    raito: Raito = message.bot.get("raito")

    # Получаем всех с ролью "tester"
    banned_users = await raito.role_manager.get_users(bot.id, "tester")

    if not banned_users:
        await message.answer("✅ Нет забаненных пользователей")
        return

    text = "🚫 <b>Забаненные пользователи:</b>\n\n"
    for user_id in banned_users:
        text += f"├ <code>{user_id}</code>\n"

    await message.answer(text)