import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.connections import router as connections_router
from app.api.v1.verifications import router as verifications_router
from app.bot.handler import extract_telegram_user, parse_start_token
from app.core.dependencies import get_db
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import api_key, project, telegram_connection, verification  # noqa: F401
from app.services import verification_service
from app.services.verification_service import VerificationError


async def _expiry_loop():
    while True:
        await asyncio.sleep(30)
        try:
            async with SessionLocal() as db:
                await verification_service.expire_sweep(db)
        except Exception:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


app = FastAPI(title="harry", lifespan=lifespan)
app.include_router(verifications_router, prefix="/v1/verifications", tags=["verifications"])
app.include_router(
    connections_router, prefix="/v1/telegram/connections", tags=["connections"]
)

try:
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    candidates = [
        Path(__file__).resolve().parent.parent / "frontend",
        Path(__file__).resolve().parent.parent.parent / "frontend",
    ]
    for frontend_dir in candidates:
        if frontend_dir.exists():
            app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
            break
except Exception:
    pass


@app.exception_handler(VerificationError)
async def verification_error_handler(request: Request, exc: VerificationError):
    return JSONResponse(
        status_code=400, content={"error": {"code": exc.code, "message": exc.message}}
    )


@app.post("/internal/telegram/webhook")
async def telegram_webhook(update: dict, db: AsyncSession = Depends(get_db)):
    user = extract_telegram_user(update)
    if user is None:
        return {"ok": True}
    token = parse_start_token(user.get("text"))
    if token is None:
        return {"ok": True}
    try:
        await verification_service.complete_via_token(
            db,
            token,
            user["telegram_user_id"],
            user["chat_id"],
            user.get("username"),
            user.get("first_name"),
        )
    except VerificationError:
        # Invalid/expired/used tokens are ignored here; status is polled by client.
        return {"ok": True}
    return {"ok": True}


@app.get("/verify/{verification_id}", response_class=HTMLResponse)
async def verify_page(verification_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    from app.models.verification import VerificationSession

    res = await db.execute(
        select(VerificationSession).where(VerificationSession.id == verification_id)
    )
    obj = res.scalar_one_or_none()
    status = obj.status if obj else "not_found"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verify your account</title></head>
<body style="font-family:system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 16px">
<h1>Verify your account</h1>
<p>Status: {status}</p>
<p>Open Telegram to complete verification, then return here. This page polls automatically.</p>
<script>
var id="{verification_id}";
setInterval(async function(){{
  try{{
    var r=await fetch("/v1/verifications/"+id,{{headers:{{}}}});
    if(r.ok){{var d=await r.json(); if(d.status==="verified"){{document.body.innerHTML="<h1>Verified</h1><p>You can return to the application.</p>";}}}}
  }}catch(e){{}}
}},3000);
</script>
</body></html>"""


@app.get("/health")
async def health():
    return {"ok": True}
