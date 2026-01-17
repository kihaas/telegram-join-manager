"""CRUD операции для всех моделей."""

from datetime import datetime, timedelta
from typing import List, Optional, Union

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    User,
    AdminSettings,
    PendingRequest,
    RequestStatus,
    CaptchaType,
    CaptchaAttempt
)


# ==================== USERS ====================

async def get_user_by_chat_id(session: AsyncSession, chat_id: int) -> Optional[User]:
    """Получить пользователя по chat_id."""
    result = await session.execute(select(User).where(User.chat_id == chat_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, chat_id: int, username: Optional[str] = None) -> User:
    """Создать нового пользователя."""
    registration_date = datetime.now().strftime("%d.%m.%Y")
    user = User(
        chat_id=chat_id,
        username=username,
        registration_date=registration_date
    )
    session.add(user)
    await session.flush()
    return user


async def get_all_chat_ids(session: AsyncSession) -> List[int]:
    """Получить все chat_id для рассылки."""
    result = await session.execute(select(User.chat_id))
    return [row[0] for row in result.all()]


async def get_users_count(session: AsyncSession) -> int:
    """Общее количество пользователей."""
    result = await session.execute(select(func.count(User.id)))
    return result.scalar() or 0


async def get_new_users_count(session: AsyncSession, days: int = 1) -> int:
    """Количество новых пользователей за N дней."""
    # Вычисляем дату N дней назад
    cutoff_date = datetime.now() - timedelta(days=days)

    # Получаем всех пользователей и фильтруем по дате
    result = await session.execute(select(User))
    users = result.scalars().all()

    count = 0
    for user in users:
        try:
            # Парсим дату формата DD.MM.YYYY
            user_date = datetime.strptime(user.registration_date, "%d.%m.%Y")
            if user_date >= cutoff_date:
                count += 1
        except (ValueError, AttributeError):
            continue

    return count


# ==================== ADMIN SETTINGS ====================

async def get_admin_settings(session: AsyncSession, settings_id: int = 1) -> Optional[AdminSettings]:
    """Получить настройки админа."""
    result = await session.execute(select(AdminSettings).where(AdminSettings.id == settings_id))
    return result.scalar_one_or_none()


async def update_admin_settings(
        session: AsyncSession,
        settings_id: int = 1,
        applications: Optional[Union[str, int]] = None,  # Изменил тип
        photo: Optional[str] = None,
        buttons: Optional[str] = None
) -> AdminSettings:
    """Обновить настройки админа."""
    # Получаем текущие настройки
    stmt = select(AdminSettings).where(AdminSettings.id == settings_id)
    result = await session.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings is None:
        # Создаём, если не существует
        settings = AdminSettings(id=settings_id)
        session.add(settings)

    # ВСЕГДА обновляем все переданные поля, даже если None
    # Используем locals() чтобы определить, какие поля переданы
    passed_args = locals()

    if 'applications' in passed_args and passed_args['applications'] is not None:
        settings.applications = applications

    # Ключевое изменение: обрабатываем photo отдельно
    if 'photo' in passed_args:
        # Если photo передано в аргументах (даже если None) - обновляем
        settings.photo = photo
        print(f"[CRUD DEBUG] Устанавливаем photo = {photo}")  # Для отладки

    if 'buttons' in passed_args and passed_args['buttons'] is not None:
        settings.buttons = buttons

    # Явно помечаем как изменённый
    from sqlalchemy import inspect
    insp = inspect(settings)
    if insp.modified:
        print(f"[CRUD DEBUG] Изменённые поля: {insp.modified}")  # Для отладки

    await session.flush()
    return settings


# ==================== PENDING REQUESTS ====================

async def create_pending_request(
        session: AsyncSession,
        user_id: int,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
) -> PendingRequest:
    """Создать новую заявку."""
    request = PendingRequest(
        user_id=user_id,
        username=username,
        first_name=first_name,
        chat_id=chat_id,
        status=RequestStatus.PENDING
    )
    session.add(request)
    await session.flush()
    return request


async def get_pending_requests(
        session: AsyncSession,
        status: Optional[RequestStatus] = None,
        limit: int = 10,
        offset: int = 0,
        order_by: str = "desc"
) -> List[PendingRequest]:
    """Получить список заявок с пагинацией."""
    query = select(PendingRequest)

    if status:
        query = query.where(PendingRequest.status == status)

    if order_by == "desc":
        query = query.order_by(PendingRequest.request_time.desc())
    else:
        query = query.order_by(PendingRequest.request_time.asc())

    query = query.limit(limit).offset(offset)

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_pending_count(session: AsyncSession, status: Optional[RequestStatus] = None) -> int:
    """Количество заявок по статусу."""
    query = select(func.count(PendingRequest.id))
    if status:
        query = query.where(PendingRequest.status == status)

    result = await session.execute(query)
    return result.scalar() or 0


async def update_request_status(
        session: AsyncSession,
        request_id: int,
        status: RequestStatus,
        processed_by: Optional[int] = None
) -> Optional[PendingRequest]:
    """Обновить статус заявки."""
    request = await session.get(PendingRequest, request_id)
    if request:
        request.status = status
        request.processed_at = datetime.utcnow()
        if processed_by:
            request.processed_by = processed_by
        await session.flush()
    return request


async def bulk_update_requests(
        session: AsyncSession,
        request_ids: List[int],
        status: RequestStatus,
        processed_by: Optional[int] = None
) -> int:
    """Массовое обновление статусов заявок."""
    stmt = (
        update(PendingRequest)
        .where(PendingRequest.id.in_(request_ids))
        .values(
            status=status,
            processed_at=datetime.utcnow(),
            processed_by=processed_by
        )
    )
    result = await session.execute(stmt)
    return result.rowcount


# ==================== CAPTCHA ATTEMPTS ====================

async def create_captcha_attempt(
        session: AsyncSession,
        user_id: int,
        chat_id: int,
        captcha_type: CaptchaType,
        is_successful: bool,
        attempts_count: int = 1
) -> CaptchaAttempt:
    """Записать попытку прохождения капчи."""
    attempt = CaptchaAttempt(
        user_id=user_id,
        chat_id=chat_id,
        captcha_type=captcha_type,
        is_successful=is_successful,
        attempts_count=attempts_count
    )
    session.add(attempt)
    await session.flush()
    return attempt


