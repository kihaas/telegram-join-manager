from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    waiting_content = State()
    preview = State()
    confirm = State()
    running = State()


class WelcomeStates(StatesGroup):
    """Состояния для редактирования приветствия."""

    waiting_content = State()  # Ожидание текста/медиа
    preview = State()  # Предпросмотр


class CaptchaStates(StatesGroup):
    """Состояния для капчи."""

    waiting_answer = State()  # Ожидание ответа на капчу


class RequestsStates(StatesGroup):
    """Состояния для управления заявками."""

    viewing_list = State()  # Просмотр списка
    multi_select = State()  # Множественный выбор


class AdminStates(StatesGroup):
    """Общие админские состояния."""

    waiting_user_id = State()  # Ожидание ID пользователя (для бана/разбана)