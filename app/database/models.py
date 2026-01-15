from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, DateTime, Enum, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class User(Base):
    """Модель пользователя (совместима со старой БД applications.db)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    registration_date: Mapped[str] = mapped_column(String(50), nullable=False)  # Формат: DD.MM.YYYY

    def __repr__(self) -> str:
        return f"<User(id={self.id}, chat_id={self.chat_id}, username={self.username})>"


class AdminSettings(Base):
    """Настройки администратора (совместима со старой БД)."""

    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applications: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)  # 0/1 для auto-accept
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # file_id фото/видео
    buttons: Mapped[str] = mapped_column(Text, default='[]', nullable=False)  # JSON строка с кнопками

    def __repr__(self) -> str:
        return f"<AdminSettings(id={self.id}, applications={self.applications})>"


class RequestStatus(PyEnum):
    """Статусы заявок на вступление."""
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    BANNED = "banned"


class PendingRequest(Base):
    """Заявки на вступление в группу."""

    __tablename__ = "pending_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ID группы/канала
    request_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus),
        default=RequestStatus.PENDING,
        nullable=False,
        index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # admin user_id

    __table_args__ = (
        Index('idx_status_time', 'status', 'request_time'),
    )

    def __repr__(self) -> str:
        return f"<PendingRequest(id={self.id}, user_id={self.user_id}, status={self.status.value})>"


class CaptchaType(PyEnum):
    """Типы капчи."""
    EMOJI = "emoji"
    IMAGE = "image"
    MATH = "math"


class CaptchaVariant(Base):
    """Варианты капчи."""

    __tablename__ = "captcha_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[CaptchaType] = mapped_column(Enum(CaptchaType), nullable=False, index=True)
    content: Mapped[str] = mapped_column(String(255), nullable=False)  # Смайлик, file_id или выражение
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    group_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Для группировки вариантов

    __table_args__ = (
        Index('idx_type_group', 'type', 'group_id'),
    )

    def __repr__(self) -> str:
        return f"<CaptchaVariant(id={self.id}, type={self.type.value}, content={self.content})>"


class BroadcastStatus(PyEnum):
    """Статусы рассылки."""
    DRAFT = "draft"
    SENDING = "sending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BroadcastDraft(Base):
    """Черновики и история рассылок."""

    __tablename__ = "broadcast_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # file_id фото/видео/документа
    buttons: Mapped[str] = mapped_column(Text, default='[]', nullable=False)  # JSON строка
    creator_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus),
        default=BroadcastStatus.DRAFT,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_sends: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_sends: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<BroadcastDraft(id={self.id}, status={self.status.value}, creator_id={self.creator_id})>"


class WelcomeVariant(Base):
    """Варианты приветственных сообщений (для A/B тестирования)."""

    __tablename__ = "welcome_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    media_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    buttons: Mapped[str] = mapped_column(Text, default='[]', nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Вес для случайного выбора
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agrees_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Кликов на "Согласен"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<WelcomeVariant(id={self.id}, is_active={self.is_active}, views={self.views_count})>"


class CaptchaAttempt(Base):
    """История попыток прохождения капчи."""

    __tablename__ = "captcha_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    captcha_type: Mapped[CaptchaType] = mapped_column(Enum(CaptchaType), nullable=False)
    is_successful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempt_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    attempts_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index('idx_user_time', 'user_id', 'attempt_time'),
    )

    def __repr__(self) -> str:
        return f"<CaptchaAttempt(user_id={self.user_id}, successful={self.is_successful})>"