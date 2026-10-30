"""使用隔离的本地数据库验证登录、记录归属和服务就绪状态。"""
import asyncio
import sqlite3
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    from fastapi.testclient import TestClient

    folder = tmp_path_factory.mktemp("login")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{folder / 'app.db'}")
        patch.setenv("UPLOAD_DIR", str(folder / "uploads"))
        patch.setenv("ZHIPUAI_API_KEY", "")
        from app.main import app
        with TestClient(app) as client:
            yield client


def register(client, name):
    response = client.post("/api/auth/register", json={
        "email": f"{name}@example.com", "username": name, "password": "test-pass-123",
    })
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_login_generate_and_history_ownership(service):
    first = register(service, "first")
    second = register(service, "second")
    login = service.post("/api/auth/token", data={
        "username": "second@example.com", "password": "test-pass-123",
    })
    assert login.status_code == 200
    assert service.get("/api/auth/me", headers=second).json()["username"] == "second"
    wrong = service.post("/api/auth/token", data={
        "username": "second@example.com", "password": "wrong-pass",
    })
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "邮箱或密码错误"

    generated = service.post("/api/prompts/generate", headers=second, data={
        "product_name": "保温杯", "selling_points": "便携保温", "count": "1", "use_ai": "false",
    }, files={
        "image": ("test.png", b"test-image", "image/png"),
        "video": ("test.mp4", b"test-video", "video/mp4"),
    })
    assert generated.status_code == 200, generated.text
    history_id = generated.json()["history_id"]
    assert history_id is not None
    own = service.get("/api/prompts/history", headers=second).json()["items"]
    assert [item["id"] for item in own] == [history_id]
    assert service.get("/api/prompts/history", headers=first).json()["items"] == []
    for media, content in [("image", b"test-image"), ("video", b"test-video")]:
        url = f"/api/prompts/history/{history_id}/{media}"
        assert service.get(url, headers=second).content == content
        assert service.get(url, headers=first).status_code == 404
        assert service.get(url).status_code == 401
    assert service.post(f"/api/prompts/history/{history_id}/share", headers=first).status_code == 404
    share = service.post(f"/api/prompts/history/{history_id}/share", headers=second)
    assert share.status_code == 200
    assert service.get(f"/api/prompts/share/{share.json()['share_token']}").status_code == 200


def test_private_routes_require_login(service):
    assert service.get("/api/prompts/history").status_code == 401
    assert service.post("/api/prompts/generate", data={"product_name": "test"}).status_code == 401
    assert service.post("/api/prompts/analyze-image", files={"image": ("test.png", b"test", "image/png")}).status_code == 401
    assert service.get("/api/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_health_checks_database(service, monkeypatch):
    from app import main

    assert service.get("/health").json() == {"status": "healthy", "database": "ok"}
    with monkeypatch.context() as patch:
        patch.setattr(main.app.state, "database_ready", False)
        assert service.get("/health").status_code == 503
    with monkeypatch.context() as patch:
        patch.setattr(main, "engine", Mock(connect=Mock(side_effect=RuntimeError("offline"))))
        assert service.get("/health").status_code == 503


def test_startup_rejects_unavailable_database(service, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main

    monkeypatch.setattr(main, "init_db", AsyncMock(side_effect=RuntimeError("offline")))
    with pytest.raises(RuntimeError, match="offline"):
        with TestClient(main.app):
            pass


def test_existing_schema_migration_preserves_records(service, tmp_path, monkeypatch):
    from sqlalchemy import inspect, text
    from sqlalchemy.ext.asyncio import create_async_engine
    from app import database

    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE prompt_histories (id INTEGER PRIMARY KEY, product_name VARCHAR(255), platform VARCHAR(50))")
        conn.execute("INSERT INTO prompt_histories VALUES (7, '原有记录', 'douyin')")

    async def migrate():
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        monkeypatch.setattr(database, "engine", engine)
        try:
            await database.init_db()
            await database.init_db()
            async with engine.connect() as conn:
                columns = await conn.run_sync(lambda sync: {c["name"] for c in inspect(sync).get_columns("prompt_histories")})
                assert {"platform", "video_data", "style_weights", "generated_count"} <= columns
                assert (await conn.execute(text("SELECT product_name FROM prompt_histories WHERE id=7"))).scalar_one() == "原有记录"
        finally:
            await engine.dispose()

    asyncio.run(migrate())
