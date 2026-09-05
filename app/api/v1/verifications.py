from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db, get_project
from app.core.rate_limit import limiter
from app.models.project import Project
from app.schemas.verification import (
    VerificationCreateRequest,
    VerificationCreateResponse,
    VerificationStatusResponse,
)
from app.services import verification_service
from app.services.verification_service import VerificationError, build_urls

router = APIRouter()


def _err(code: str, message: str, status: int = 400):
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message}}
    )


@router.post("", response_model=VerificationCreateResponse)
async def create_verification(
    payload: VerificationCreateRequest,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    ok = await limiter.allow(
        f"create:{project.id}",
        settings.rate_limit_per_minute,
    )
    if not ok:
        return _err("RATE_LIMIT_EXCEEDED", "Too many requests.", 429)
    try:
        obj, token = await verification_service.create_session(
            db, project.id, payload.external_user_id, payload.metadata
        )
    except VerificationError as e:
        return _err(e.code, e.message, 429)
    verification_url, telegram_url = build_urls(obj.id, token)
    return VerificationCreateResponse(
        id=obj.id,
        status=obj.status,
        verification_url=verification_url,
        telegram_url=telegram_url,
        expires_at=obj.expires_at,
    )


@router.get("/{verification_id}", response_model=VerificationStatusResponse)
async def get_verification(
    verification_id: str,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    try:
        obj = await verification_service.get_session(db, project.id, verification_id)
    except VerificationError as e:
        return _err(e.code, e.message, 404)
    return VerificationStatusResponse(
        id=obj.id,
        status=obj.status,
        external_user_id=obj.external_user_id,
        verified_at=obj.verified_at,
        expires_at=obj.expires_at,
    )


@router.post("/{verification_id}/cancel")
async def cancel_verification(
    verification_id: str,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    try:
        obj = await verification_service.cancel_session(db, project.id, verification_id)
    except VerificationError as e:
        code = 404 if e.code == "VERIFICATION_NOT_FOUND" else 409
        return _err(e.code, e.message, code)
    return {"id": obj.id, "status": obj.status}


@router.post("/{verification_id}/retry", response_model=VerificationCreateResponse)
async def retry_verification(
    verification_id: str,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    try:
        obj, token = await verification_service.retry_session(
            db, project.id, verification_id
        )
    except VerificationError as e:
        return _err(e.code, e.message, 404)
    verification_url, telegram_url = build_urls(obj.id, token)
    return VerificationCreateResponse(
        id=obj.id,
        status=obj.status,
        verification_url=verification_url,
        telegram_url=telegram_url,
        expires_at=obj.expires_at,
    )
