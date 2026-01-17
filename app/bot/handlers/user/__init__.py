from aiogram import Router

from app.bot.handlers.user.commands.join_requests import router as join_router

# Главный роутер для пользователей
user_router = Router()

# Подключаем все user роутеры
user_router.include_router(join_router)


__all__ = ["user_router"]