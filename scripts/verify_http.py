import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models.api_key import ApiKey
from app.core.security import hash_key

async def main():
    # get latest key raw would not be stored hashed, need to create a known key for http test
    from app.core.security import generate_api_key, new_id
    raw = generate_api_key("sk_live_")
    # insert it
    from app.models.project import Project
    async with SessionLocal() as db:
        res = await db.execute(select(Project).where(Project.slug=="test-project"))
        project = res.scalar_one()
        k = ApiKey(id=new_id("key_"), project_id=project.id, key_hash=hash_key(raw), key_prefix=raw[:12], type="secret")
        db.add(k)
        await db.commit()
        print(f"http test key: {raw}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # create verification
        r = await client.post("/v1/verifications", json={"external_user_id":"http_user_1","metadata":{"purpose":"http_test"}}, headers={"Authorization": f"Bearer {raw}"})
        print("POST /v1/verifications", r.status_code, r.json())
        assert r.status_code == 200
        data = r.json()
        vid = data["id"]
        # extract token from telegram_url
        import re
        m = re.search(r"start=([^&]+)", data["telegram_url"])
        token = m.group(1) if m else None
        print(f"token for webhook: {token[:8]}***")

        # poll before
        r2 = await client.get(f"/v1/verifications/{vid}", headers={"Authorization": f"Bearer {raw}"})
        print("GET before", r2.json())

        # telegram webhook
        update = {"message": {"text": f"/start {token}", "from": {"id": 999888777, "username": "httptest", "first_name": "Http"}, "chat": {"id": 999888777}}}
        r3 = await client.post("/internal/telegram/webhook", json=update)
        print("POST webhook", r3.json())

        # poll after
        r4 = await client.get(f"/v1/verifications/{vid}", headers={"Authorization": f"Bearer {raw}"})
        print("GET after", r4.json())
        assert r4.json()["status"] == "verified"

        # connection
        r5 = await client.get(f"/v1/telegram/connections/http_user_1", headers={"Authorization": f"Bearer {raw}"})
        print("GET connection", r5.json())
        assert r5.json()["connected"] is True

        # hosted page
        r6 = await client.get(f"/verify/{vid}")
        print("GET /verify page", r6.status_code, "html" if "text/html" in r6.headers.get("content-type","") else r6.headers)

        print("http integration: PASS")

if __name__ == "__main__":
    asyncio.run(main())
