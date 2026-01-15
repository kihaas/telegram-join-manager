from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Основная конфигурация бота."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # === Bot Settings ===
    bot_token: str = Field(..., description="Telegram Bot Token")
    parse_mode: str = Field(default="HTML", description="Default parse mode")

    # === Admin Settings ===
    developers: List[int] = Field(default_factory=list, description="Developer IDs")
    admin_ids: List[int] = Field(default_factory=list, description="Admin IDs")

    # === Database Settings ===
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/applications.db",
        description="Database URL"
    )

    # === Redis Settings ===
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for FSM and cache"
    )

    # === Features Toggles ===
    captcha_enabled: bool = Field(default=True, description="Enable captcha verification")
    auto_accept_default: bool = Field(default=False, description="Auto-accept join requests by default")
    notify_on_new_request: bool = Field(default=False, description="Notify admins on new requests")

    # === Captcha Settings ===
    captcha_timeout_min: int = Field(default=5, description="Captcha timeout in minutes")
    captcha_max_attempts: int = Field(default=3, description="Max captcha attempts before ban")

    # === Broadcast Settings ===
    broadcast_semaphore_limit: int = Field(default=5, description="Concurrent broadcast tasks")
    broadcast_delay: float = Field(default=0.036, description="Delay between messages (seconds)")
    broadcast_retry_attempts: int = Field(default=2, description="Retry attempts for failed sends")

    # === Notifications ===
    notify_interval_min: int = Field(default=10, description="Notification interval in minutes")

    # === Paths ===
    captcha_image_path: str = Field(default="assets/captcha.png", description="Path to captcha image")
    log_file: str = Field(default="logs/app.log", description="Log file path")

    # === Options ===
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("developers", "admin_ids", mode="before")
    @classmethod
    def parse_ids(cls, v):
        """Парсинг ID из строки или списка."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(id.strip()) for id in v.split(",") if id.strip().isdigit()]
        if isinstance(v, int):
            return [v]
        if isinstance(v, list):
            return v
        return []

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Валидация уровня логирования."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_levels)}")
        return v

    @property
    def all_admins(self) -> List[int]:
        """Объединённый список всех админов (developers + admin_ids)."""
        return list(set(self.developers + self.admin_ids))


# Глобальный экземпляр конфига
config: Config | None = None


def load_config() -> Config:
    """Загрузка конфигурации (singleton)."""
    global config
    if config is None:
        config = Config()
    return config


def get_config() -> Config:
    """Получение текущего конфига."""
    if config is None:
        raise RuntimeError("Config not loaded. Call load_config() first.")
    return config