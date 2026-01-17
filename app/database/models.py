"""Все модели базы данных в одном файле."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, DateTime, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


# ==================== USER ====================
class User(Base):
    """Модель пользователя (совместима со старой БД applications.db)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    registration_date: Mapped[str] = mapped_column(String(50), nullable=False)  # Формат: DD.MM.YYYY

    def __repr__(self) -> str:
        return f"<User(id={self.id}, chat_id={self.chat_id}, username={self.username})>"


# ==================== ADMIN SETTINGS ====================
class AdminSettings(Base):
    """Настройки администратора (совместима со старой БД)."""

    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applications: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)  # 0/1 для auto-accept
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # file_id фото/видео
    buttons: Mapped[str] = mapped_column(Text, default='[]', nullable=False)  # JSON строка с кнопками

    def __repr__(self) -> str:
        return f"<AdminSettings(id={self.id}, applications={self.applications})>"


# ==================== ЗАЯВКИ ====================
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


# ==================== КАПЧА ====================
class CaptchaType(PyEnum):
    """Типы капчи."""
    EMOJI = "emoji"  # Только emoji капча


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