from aiogram import Router

from .join_request import router as join_router
from .captcha import router as captcha_router

# Главный роутер для пользователей
user_router = Router()

# Подключаем все user роутеры
user_router.include_router(join_router)
user_router.include_router(captcha_router)

__all__ = ["user_router"]