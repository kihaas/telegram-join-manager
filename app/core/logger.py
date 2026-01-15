import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import cast, Literal

from colorama import Fore, Style, init

# Инициализация colorama для Windows
init(autoreset=True)

LEVEL = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Цвета для уровней логирования
LEVEL_COLORS: dict[LEVEL, str] = {
    "DEBUG": Fore.CYAN,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED + Style.BRIGHT,
}

# Цвета для фона тегов
TAG_BACKGROUND: dict[LEVEL, str] = {
    "DEBUG": Fore.CYAN + Style.BRIGHT,
    "INFO": Fore.GREEN + Style.BRIGHT,
    "WARNING": Fore.YELLOW + Style.BRIGHT,
    "ERROR": Fore.RED + Style.BRIGHT,
    "CRITICAL": Fore.RED + Style.BRIGHT,
}


class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для консоли."""

    def format(self, record: logging.LogRecord) -> str:
        levelname = cast(LEVEL, record.levelname)

        # Временная метка
        timestamp = datetime.fromtimestamp(record.created).strftime("%d.%m.%Y %H:%M:%S")
        timestamp_colored = f"{Fore.BLACK + Style.BRIGHT}{timestamp}{Style.RESET_ALL}"

        # Имя логгера
        logger_name = f"{Fore.WHITE}{record.name}{Style.RESET_ALL}"

        # Тег уровня с цветом
        tag_color = TAG_BACKGROUND.get(levelname, "")
        tag = f"{tag_color}[{levelname[0]}]{Style.RESET_ALL}"

        # Сообщение с цветом
        msg_color = LEVEL_COLORS.get(levelname, "")
        message = f"{msg_color}{record.getMessage()}{Style.RESET_ALL}"

        # Формируем строку с отступами
        left_part = f"{timestamp_colored} {logger_name}"
        spacing = " " * max(1, 64 - len(record.name) - 20)

        return f"{left_part}{spacing}{tag} {message}"


class FileFormatter(logging.Formatter):
    """Форматтер для файлов (без цветов)."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"{timestamp} [{record.levelname}] {record.name}: {record.getMessage()}"


def setup_logger(log_file: str = "logs/app.log", log_level: str = "INFO") -> logging.Logger:
    """
    Настройка логирования для всего приложения.

    Args:
        log_file: Путь к файлу логов
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Настроенный root logger
    """
    # Получаем root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # === Консольный handler ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)

    # === Файловый handler с ротацией ===
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(FileFormatter())
        root_logger.addHandler(file_handler)

        root_logger.info(f"📁 Логирование в файл: {log_file}")

    except Exception as e:
        root_logger.warning(f"⚠️ Не удалось настроить файловое логирование: {e}")

    # Отключаем шумные логи aiogram
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.WARNING)
    logging.getLogger("aiogram.middlewares").setLevel(logging.WARNING)
    logging.getLogger("aiogram.webhook").setLevel(logging.WARNING)

    # Отключаем шумные логи SQLAlchemy
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Получить логгер для конкретного модуля."""
    return logging.getLogger(name)