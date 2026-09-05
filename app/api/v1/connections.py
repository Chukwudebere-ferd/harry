from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_project
from app.models.project import Project
from app.models.telegram_connection import TelegramConnection
from app.schemas.connection import ConnectionResponse

router = APIRouter()


@router.get("/{external_user_id}", response_model=ConnectionResponse)
async def get_connection(
    external_user_id: str,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(TelegramConnection).where(
            TelegramConnection.project_id == project.id,
            TelegramConnection.external_user_id == external_user_id,
        )
    )
    conn = res.scalar_one_or_none()
    if conn is None:
        return ConnectionResponse(connected=False)
    return ConnectionResponse(
        connected=True,
        telegram_user_id=str(conn.telegram_user_id),
        connected_at=conn.connected_at,
    )
