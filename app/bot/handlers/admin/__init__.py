from aiogram import Router

from .menu import router as menu_router
from .requests import router as requests_router
from .welcome import router as welcome_router

# Главный роутер для админов
admin_router = Router()

# Подключаем все админские роутеры
admin_router.include_router(menu_router)
admin_router.include_router(requests_router)
admin_router.include_router(welcome_router)

__all__ = ["admin_router"]