from aiogram import Router

from app.bot.handlers.admin.commands.menu import router as menu_router
from app.bot.handlers.admin.commands.requests import router as requests_router
from app.bot.handlers.admin.commands.welcome import router as welcome_router
from app.services.broadcast import router as broudcast_router

# Главный роутер для пользователей
admin_router = Router()

# Подключаем все user роутеры
admin_router.include_router(menu_router)
admin_router.include_router(requests_router)
admin_router.include_router(welcome_router)
admin_router.include_router(broudcast_router)

__all__ = ["admin_router"]