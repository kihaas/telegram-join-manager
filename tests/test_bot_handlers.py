# tests/test_bot_handlers.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import router  # или другое имя, где лежит router


@pytest.fixture
def message():
    msg = MagicMock(spec=Message)
    msg.text = ""
    msg.answer = AsyncMock()
    msg.from_user.id = 936169200
    msg.from_user.full_name = "Test User"
    msg.from_user.username = "testuser"
    return msg


@pytest.fixture
def state():
    storage = MemoryStorage()
    key = MagicMock()
    return AsyncMock(spec=FSMContext, storage=storage, key=key)


class TestBotHandlers:

    async def test_start_command(self, message, state):
        """Тест команды /start."""
        handler = router.message.handlers[0].callback
        await handler(message, state)
        message.answer.assert_called()
        assert "приветственное сообщение" in message.answer.await_args.kwargs.get("text", "").lower()


    async def test_help_command(self, message, state):
        """Тест команды /help."""
        handler = None
        for h in router.message.handlers:
            if Command("help") in h.filters:
                handler = h.callback
                break

        if handler:
            await handler(message, state)
            message.answer.assert_called()
            assert "помощь" in message.answer.await_args.kwargs.get("text", "").lower()