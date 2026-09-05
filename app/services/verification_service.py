from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_verification_token, hash_token, new_id
from app.models.telegram_connection import TelegramConnection
from app.models.verification import (
    CANCELLED,
    EXPIRED,
    PENDING,
    VERIFIED,
    VerificationSession,
)


class VerificationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_urls(verification_id: str, token: str) -> tuple[str, str]:
    base = settings.api_base_url.rstrip("/")
    return (
        f"{base}/verify/{verification_id}",
        f"https://t.me/{settings.bot_username}?start={token}",
    )


async def _pending_count(db: AsyncSession, project_id: str) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(VerificationSession)
        .where(
            VerificationSession.project_id == project_id,
            VerificationSession.status == PENDING,
        )
    )
    return int(res.scalar_one())


async def create_session(
    db: AsyncSession,
    project_id: str,
    external_user_id: str,
    metadata: dict | None,
) -> tuple[VerificationSession, str]:
    if await _pending_count(db, project_id) >= settings.max_pending_per_project:
        raise VerificationError("RATE_LIMIT_EXCEEDED", "Too many pending sessions.")

    token = generate_verification_token()
    now = _utcnow()
    session = VerificationSession(
        id=new_id("vrf_"),
        project_id=project_id,
        external_user_id=external_user_id,
        token_hash=hash_token(token),
        status=PENDING,
        extra_metadata=metadata,
        expires_at=now + timedelta(seconds=settings.verification_ttl_seconds),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session, token


async def get_session(
    db: AsyncSession, project_id: str, verification_id: str
) -> VerificationSession:
    res = await db.execute(
        select(VerificationSession).where(
            VerificationSession.id == verification_id,
            VerificationSession.project_id == project_id,
        )
    )
    obj = res.scalar_one_or_none()
    if obj is None:
        raise VerificationError("VERIFICATION_NOT_FOUND", "Verification not found.")
    if obj.status == PENDING and obj.expires_at <= _utcnow():
        obj.status = EXPIRED
        await db.commit()
        await db.refresh(obj)
    return obj


async def cancel_session(
    db: AsyncSession, project_id: str, verification_id: str
) -> VerificationSession:
    obj = await get_session(db, project_id, verification_id)
    if obj.status != PENDING:
        raise VerificationError(
            "VERIFICATION_ALREADY_USED", "Only pending sessions can be cancelled."
        )
    obj.status = CANCELLED
    await db.commit()
    await db.refresh(obj)
    return obj


async def retry_session(
    db: AsyncSession, project_id: str, verification_id: str
) -> tuple[VerificationSession, str]:
    old = await get_session(db, project_id, verification_id)
    return await create_session(db, project_id, old.external_user_id, old.extra_metadata)


async def complete_via_token(
    db: AsyncSession,
    token: str,
    telegram_user_id: int,
    chat_id: int,
    username: str | None,
    first_name: str | None,
) -> VerificationSession:
    digest = hash_token(token)
    res = await db.execute(
        select(VerificationSession).where(VerificationSession.token_hash == digest)
    )
    obj = res.scalar_one_or_none()
    if obj is None:
        raise VerificationError("INVALID_VERIFICATION_TOKEN", "Invalid token.")
    if obj.status != PENDING:
        raise VerificationError("VERIFICATION_ALREADY_USED", "Token already used.")
    if obj.expires_at <= _utcnow():
        obj.status = EXPIRED
        await db.commit()
        raise VerificationError("VERIFICATION_EXPIRED", "Session expired.")

    now = _utcnow()
    obj.status = VERIFIED
    obj.verified_at = now
    obj.telegram_user_id = str(telegram_user_id)

    # Upsert connection: one per (project, external_user)
    cres = await db.execute(
        select(TelegramConnection).where(
            TelegramConnection.project_id == obj.project_id,
            TelegramConnection.external_user_id == obj.external_user_id,
        )
    )
    conn = cres.scalar_one_or_none()
    if conn is None:
        conn = TelegramConnection(
            id=new_id("tgc_"),
            project_id=obj.project_id,
            external_user_id=obj.external_user_id,
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
        )
        db.add(conn)
    else:
        conn.telegram_user_id = telegram_user_id
        conn.chat_id = chat_id
        conn.username = username
        conn.first_name = first_name
        conn.last_active_at = now

    await db.commit()
    await db.refresh(obj)
    return obj


async def expire_sweep(db: AsyncSession) -> int:
    res = await db.execute(
        select(VerificationSession).where(
            VerificationSession.status == PENDING,
            VerificationSession.expires_at <= _utcnow(),
        ).limit(500)
    )
    rows = list(res.scalars())
    for r in rows:
        r.status = EXPIRED
    if rows:
        await db.commit()
    return len(rows)
