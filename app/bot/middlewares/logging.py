import time
import traceback
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from app.core import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех обновлений и ошибок."""

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        """Обрабатываем обновление с логированием."""

        # Получаем информацию о юзере
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id
        elif hasattr(event, "chat") and event.chat:
            user_id = event.chat.id

        # Получаем название обработчика
        handler_name = data.get("handler", {})
        if hasattr(handler_name, "callback"):
            handler_name = handler_name.callback.__name__
        else:
            handler_name = "unknown"

        # Тип события
        event_type = type(event).__name__

        # Засекаем время
        start_time = time.perf_counter()
        exception = None

        try:
            # Выполняем handler
            result = await handler(event, data)
            return result

        except TelegramForbiddenError:
            # Юзер заблокировал бота
            if user_id:
                logger.info(f"[id{user_id}] Пользователь заблокировал бота")
            return None

        except TelegramBadRequest as e:
            # Некорректный запрос к API
            logger.warning(f"[id{user_id}] TelegramBadRequest: {e}")
            return None

        except Exception:
            # Любая другая ошибка
            exception = traceback.format_exc()
            raise

        finally:
            # Считаем время выполнения
            duration = (time.perf_counter() - start_time) * 1000

            # Логируем
            log_msg = f"[id{user_id}] [{duration:.0f}ms] [{event_type}] -> {handler_name}"

            if exception:
                logger.error(f"{log_msg}\n{exception}")
            else:
                logger.info(log_msg)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для защиты от спама (rate limiting).

    Ограничивает количество запросов от одного пользователя.
    """

    def __init__(self, rate_limit: float = 0.5):
        """
        Args:
            rate_limit: Минимальное время между запросами (секунды)
        """
        self.rate_limit = rate_limit
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        """Проверяем rate limit для пользователя."""

        # Получаем user_id
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        # Проверяем последний запрос
        current_time = time.time()
        last_time = self.user_timestamps.get(user_id, 0)

        if current_time - last_time < self.rate_limit:
            # Слишком частые запросы
            logger.warning(f"[id{user_id}] Rate limit exceeded")
            return None

        # Обновляем timestamp
        self.user_timestamps[user_id] = current_time

        # Очищаем старые записи (если накопилось > 1000)
        if len(self.user_timestamps) > 1000:
            cutoff = current_time - 60  # Удаляем старше 1 минуты
            self.user_timestamps = {
                uid: ts for uid, ts in self.user_timestamps.items()
                if ts > cutoff
            }

        return await handler(event, data)