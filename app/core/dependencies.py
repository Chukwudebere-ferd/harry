from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_key
from app.db.session import SessionLocal
from app.models.api_key import ApiKey
from app.models.project import Project


async def get_db():
    async with SessionLocal() as db:
        yield db


async def get_project(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Project:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="INVALID_API_KEY")
    raw = authorization[7:]
    res = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_key(raw)))
    key = res.scalar_one_or_none()
    if key is None or key.revoked_at is not None:
        raise HTTPException(status_code=401, detail="INVALID_API_KEY")
    res = await db.execute(select(Project).where(Project.id == key.project_id))
    project = res.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=401, detail="PROJECT_NOT_FOUND")
    return project
