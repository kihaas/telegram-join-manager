from aiogram import Router

from .admin import admin_router
from .user import user_router

# Главный роутер приложения
main_router = Router()

# Подключаем роутеры (порядок важен - сначала admin)
main_router.include_router(admin_router)
main_router.include_router(user_router)

__all__ = ["main_router", "admin_router", "user_router"]