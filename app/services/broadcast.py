from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from raito.plugins.roles import DEVELOPER, OWNER, ADMINISTRATOR

from app.core import get_logger
from app.bot.keyboards import get_back_to_menu

logger = get_logger(__name__)
router = Router()


@router.message(F.text == "📩 Рассылка", DEVELOPER | OWNER | ADMINISTRATOR)
@router.callback_query(F.data == "admin:broadcast", DEVELOPER | OWNER | ADMINISTRATOR)
async def broadcast_menu(event: Message | CallbackQuery) -> None:
    """
    Меню рассылки.

    TODO: Полная реализация в следующем этапе
    """
    text = (
        "📩 <b>Рассылка</b>\n\n"
        "🚧 Раздел в разработке...\n\n"
        "Скоро здесь будут:\n"
        "├ Создание черновиков\n"
        "├ Предпросмотр\n"
        "├ Тестовая отправка\n"
        "├ Запуск рассылки\n"
        "└ Статистика в реальном времени"
    )

    if isinstance(event, Message):
        await event.answer(text, reply_markup=get_back_to_menu())
    else:
        await event.message.edit_text(text, reply_markup=get_back_to_menu())
        await event.answer()