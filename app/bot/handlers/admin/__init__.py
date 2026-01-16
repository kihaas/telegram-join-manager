from aiogram import Router

from .menu import router as menu_router

# Главный роутер для админов
admin_router = Router()

# Подключаем все админские роутеры
admin_router.include_router(menu_router)

__all__ = ["admin_router"]