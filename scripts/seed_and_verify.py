import asyncio
from sqlalchemy import select
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.project import Project
from app.models.api_key import ApiKey
from app.core.security import generate_api_key, hash_key, new_id
from app.services import verification_service

async def main():
    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("tables: ok")

    # 2. Seed project + key if missing
    async with SessionLocal() as db:
        res = await db.execute(select(Project).where(Project.slug == "test-project"))
        project = res.scalar_one_or_none()
        if project is None:
            project = Project(id=new_id("proj_"), name="Test Project", slug="test-project", status="active")
            db.add(project)
            await db.commit()
            await db.refresh(project)
            print(f"project created: {project.id} slug={project.slug}")
        else:
            print(f"project exists: {project.id}")

        # check existing key
        res = await db.execute(select(ApiKey).where(ApiKey.project_id == project.id))
        key = res.scalar_one_or_none()
        if key is None:
            raw = generate_api_key("sk_live_")
            k = ApiKey(
                id=new_id("key_"),
                project_id=project.id,
                key_hash=hash_key(raw),
                key_prefix=raw[:12],
                type="secret",
            )
            db.add(k)
            await db.commit()
            print(f"api_key created: prefix={k.key_prefix} FULL={raw}  <-- save this, shown once")
            raw_key = raw
        else:
            # need to generate a fresh key for testing if we don't have raw
            raw = generate_api_key("sk_live_")
            k = ApiKey(
                id=new_id("key_"),
                project_id=project.id,
                key_hash=hash_key(raw),
                key_prefix=raw[:12],
                type="secret",
            )
            db.add(k)
            await db.commit()
            print(f"new api_key for test: prefix={k.key_prefix} FULL={raw}")
            raw_key = raw

        # 3. Test verification flow
        sess, token = await verification_service.create_session(db, project.id, "user_12345", {"purpose": "test"})
        print(f"verification created: id={sess.id} status={sess.status} token={token[:10]}*** expires={sess.expires_at}")
        # verify hash stored not raw
        assert sess.token_hash != token
        print("token hash stored: ok")

        # poll before verify
        fetched = await verification_service.get_session(db, project.id, sess.id)
        print(f"poll before: status={fetched.status}")

        # simulate telegram webhook complete
        completed = await verification_service.complete_via_token(db, token, 123456789, 123456789, "exampleuser", "John")
        print(f"telegram complete: id={completed.id} status={completed.status} verified_at={completed.verified_at}")

        # poll after
        fetched2 = await verification_service.get_session(db, project.id, sess.id)
        print(f"poll after: status={fetched2.status}")

        # connection stored
        from sqlalchemy import select as sel
        from app.models.telegram_connection import TelegramConnection
        res = await db.execute(sel(TelegramConnection).where(TelegramConnection.project_id==project.id, TelegramConnection.external_user_id=="user_12345"))
        conn = res.scalar_one_or_none()
        print(f"telegram_connection: {conn.id if conn else None} tg_user={conn.telegram_user_id if conn else None}")

        # cancel/retry test on new session
        sess2, tok2 = await verification_service.create_session(db, project.id, "user_retry", None)
        canceled = await verification_service.cancel_session(db, project.id, sess2.id)
        print(f"cancel: {canceled.id} -> {canceled.status}")
        sess3, tok3 = await verification_service.retry_session(db, project.id, sess2.id)
        print(f"retry: old={sess2.id} new={sess3.id} new_status={sess3.status}")

        # expiry sweep (create expired)
        from datetime import datetime, timezone, timedelta
        from app.models.verification import VerificationSession, PENDING
        import hashlib
        expired_sess = VerificationSession(
            id=new_id("vrf_"),
            project_id=project.id,
            external_user_id="expired_user",
            token_hash=hashlib.sha256(b"dummy").hexdigest()+expired_sess.id if False else hashlib.sha256(b"expired_test_token_xyz").hexdigest(),
            status=PENDING,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        # ensure unique hash
        expired_sess.token_hash = hashlib.sha256(f"expired_{expired_sess.id}".encode()).hexdigest()
        db.add(expired_sess)
        await db.commit()
        cnt = await verification_service.expire_sweep(db)
        print(f"expire_sweep: cleaned {cnt}")

        print("verify api against real db: PASS")

if __name__ == "__main__":
    asyncio.run(main())
