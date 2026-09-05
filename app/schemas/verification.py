from datetime import datetime

from pydantic import BaseModel, Field


class VerificationCreateRequest(BaseModel):
    external_user_id: str = Field(min_length=1, max_length=200)
    metadata: dict | None = None


class VerificationCreateResponse(BaseModel):
    id: str
    status: str
    verification_url: str
    telegram_url: str
    expires_at: datetime


class VerificationStatusResponse(BaseModel):
    id: str
    status: str
    external_user_id: str
    verified_at: datetime | None = None
    expires_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
