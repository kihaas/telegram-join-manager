from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    User,
    AdminSettings,
    PendingRequest,
    RequestStatus,
    CaptchaVariant,
    CaptchaType,
    BroadcastDraft,
    BroadcastStatus,
    WelcomeVariant,
    CaptchaAttempt,
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
    target_date = (datetime.now() - timedelta(days=days)).strftime("%d.%m.%Y")
    result = await session.execute(
        select(func.count(User.id)).where(User.registration_date >= target_date)
    )
    return result.scalar() or 0


# ==================== ADMIN SETTINGS ====================

async def get_admin_settings(session: AsyncSession, settings_id: int = 1) -> Optional[AdminSettings]:
    """Получить настройки админа."""
    result = await session.execute(select(AdminSettings).where(AdminSettings.id == settings_id))
    return result.scalar_one_or_none()


async def update_admin_settings(
        session: AsyncSession,
        settings_id: int = 1,
        applications: Optional[int] = None,
        photo: Optional[str] = None,
        buttons: Optional[str] = None
) -> AdminSettings:
    """Обновить настройки админа."""
    settings = await get_admin_settings(session, settings_id)

    if settings is None:
        # Создаём, если не существует
        settings = AdminSettings(id=settings_id)
        session.add(settings)

    if applications is not None:
        settings.applications = applications
    if photo is not None:
        settings.photo = photo
    if buttons is not None:
        settings.buttons = buttons

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
        order_by: str = "desc"  # "asc" or "desc"
) -> List[PendingRequest]:
    """Получить список заявок с фильтрами и пагинацией."""
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


# ==================== CAPTCHA VARIANTS ====================

async def create_captcha_variant(
        session: AsyncSession,
        captcha_type: CaptchaType,
        content: str,
        is_correct: bool = False,
        group_id: Optional[int] = None
) -> CaptchaVariant:
    """Создать вариант капчи."""
    variant = CaptchaVariant(
        type=captcha_type,
        content=content,
        is_correct=is_correct,
        group_id=group_id
    )
    session.add(variant)
    await session.flush()
    return variant


async def get_random_captcha_variants(
        session: AsyncSession,
        captcha_type: CaptchaType,
        count: int = 4
) -> List[CaptchaVariant]:
    """Получить случайные варианты капчи."""
    result = await session.execute(
        select(CaptchaVariant)
        .where(CaptchaVariant.type == captcha_type)
        .order_by(func.random())
        .limit(count)
    )
    return list(result.scalars().all())


# ==================== BROADCAST DRAFTS ====================

async def create_broadcast_draft(
        session: AsyncSession,
        creator_id: int,
        text: Optional[str] = None,
        media_id: Optional[str] = None,
        buttons: str = "[]"
) -> BroadcastDraft:
    """Создать черновик рассылки."""
    draft = BroadcastDraft(
        text=text,
        media_id=media_id,
        buttons=buttons,
        creator_id=creator_id,
        status=BroadcastStatus.DRAFT
    )
    session.add(draft)
    await session.flush()
    return draft


async def get_broadcast_drafts(session: AsyncSession, creator_id: Optional[int] = None) -> List[BroadcastDraft]:
    """Получить черновики рассылок."""
    query = select(BroadcastDraft).order_by(BroadcastDraft.created_at.desc())
    if creator_id:
        query = query.where(BroadcastDraft.creator_id == creator_id)

    result = await session.execute(query)
    return list(result.scalars().all())


async def update_broadcast_status(
        session: AsyncSession,
        draft_id: int,
        status: BroadcastStatus,
        **kwargs
) -> Optional[BroadcastDraft]:
    """Обновить статус рассылки."""
    draft = await session.get(BroadcastDraft, draft_id)
    if draft:
        draft.status = status
        for key, value in kwargs.items():
            if hasattr(draft, key):
                setattr(draft, key, value)
        await session.flush()
    return draft


# ==================== WELCOME VARIANTS ====================

async def get_active_welcome_variants(session: AsyncSession) -> List[WelcomeVariant]:
    """Получить активные варианты приветствий."""
    result = await session.execute(
        select(WelcomeVariant)
        .where(WelcomeVariant.is_active == True)
        .order_by(WelcomeVariant.created_at.desc())
    )
    return list(result.scalars().all())


async def increment_welcome_views(session: AsyncSession, variant_id: int) -> None:
    """Увеличить счётчик просмотров приветствия."""
    await session.execute(
        update(WelcomeVariant)
        .where(WelcomeVariant.id == variant_id)
        .values(views_count=WelcomeVariant.views_count + 1)
    )


async def increment_welcome_agrees(session: AsyncSession, variant_id: int) -> None:
    """Увеличить счётчик согласий с правилами."""
    await session.execute(
        update(WelcomeVariant)
        .where(WelcomeVariant.id == variant_id)
        .values(agrees_count=WelcomeVariant.agrees_count + 1)
    )


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


async def get_captcha_success_rate(session: AsyncSession) -> float:
    """Процент успешного прохождения капчи."""
    total = await session.execute(select(func.count(CaptchaAttempt.id)))
    total_count = total.scalar() or 0

    if total_count == 0:
        return 0.0

    successful = await session.execute(
        select(func.count(CaptchaAttempt.id))
        .where(CaptchaAttempt.is_successful == True)
    )
    successful_count = successful.scalar() or 0

    return (successful_count / total_count) * 100