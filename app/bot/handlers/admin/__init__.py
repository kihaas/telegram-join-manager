from aiogram import Router

from app.bot.handlers.admin.menu import router as menu_router
from app.bot.handlers.admin.requests import router as requests_router
from app.bot.handlers.admin.welcome import router as welcome_router
from app.services.broadcast import router as broadcast_router

# Главный роутер для админов
admin_router = Router()

# Подключаем все админские роутеры
admin_router.include_router(menu_router)
admin_router.include_router(requests_router)
admin_router.include_router(welcome_router)
admin_router.include_router(broadcast_router)

__all__ = ["admin_router"]