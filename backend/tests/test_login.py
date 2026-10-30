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
        patch.setenv("STORAGE_BACKEND", "local")
        patch.delenv("RENDER", raising=False)
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


@pytest.mark.parametrize("platform", ["taobao", "douyin"])
def test_ai_generation_reaches_provider_for_single_and_multiple_groups(service, monkeypatch, platform):
    import json
    from types import SimpleNamespace
    import zhipuai
    from app.routers import prompts

    generated = [{"index": 1, "styleLabel": "高端大片风", "finalPrompt": "Cinematic product reveal.",
                  "dynamicStrategy": "Orbit", "audioPlan": "Piano"}]
    completion = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(generated, ensure_ascii=False)))]))
    monkeypatch.setattr(zhipuai, "ZhipuAI", Mock(return_value=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=completion)))))
    monkeypatch.setattr(prompts.settings, "ZHIPUAI_API_KEY", "test-provider-key")
    owner = register(service, f"ai-{platform}")
    response = service.post("/api/prompts/generate", headers=owner,
        data={"product_name": "保温杯", "platform": platform, "count": "1", "use_ai": "true"})
    assert response.status_code == 200, response.text
    completion.assert_called_once()
    result = response.json()["prompts"][0]
    assert "AI词数" in result["audit"]
    user_prompt = completion.call_args.kwargs["messages"][1]["content"]
    assert ("SEGMENT GROUPING RULE" in user_prompt) == (platform == "douyin")
    assert result["promptGroups"]


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


def test_neon_connection_verifies_tls(service):
    import ssl
    from app.config import Settings
    from app.database import database_connection_options

    settings = Settings(DATABASE_URL="postgresql://user:password@ep-test.neon.tech/db?sslmode=require&channel_binding=require")
    url, options = database_connection_options(settings.database_url)
    assert url.drivername == "postgresql+asyncpg"
    assert "sslmode" not in url.query
    assert "channel_binding" not in url.query
    assert options["connect_args"]["ssl"].verify_mode == ssl.CERT_REQUIRED
    assert options["connect_args"]["ssl"].check_hostname is True


def test_render_rejects_ephemeral_database_and_files(service, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main

    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(RuntimeError, match="外部 PostgreSQL 和持久素材存储"):
        with TestClient(main.app):
            pass


def test_s3_files_survive_client_restart_and_remain_private(service, monkeypatch):
    import io
    from pathlib import Path
    from botocore.response import StreamingBody
    from app import storage

    objects = {}

    class StorageClient:
        def put_object(self, *, Bucket, Key, Body, ContentType):
            objects[(Bucket, Key)] = (Body, ContentType)

        def get_object(self, *, Bucket, Key):
            content, content_type = objects[(Bucket, Key)]
            return {"Body": StreamingBody(io.BytesIO(content), len(content)), "ContentLength": len(content)}

    monkeypatch.setattr(storage.settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(storage.settings, "S3_BUCKET", "test-uploads")
    monkeypatch.setattr(storage, "_s3_client", StorageClient)
    files_before = set(Path(storage.settings.UPLOAD_DIR).iterdir())
    owner = register(service, "storage-owner")
    stranger = register(service, "storage-stranger")
    filename = "保温杯" * 100 + ".png"
    generated = service.post("/api/prompts/generate", headers=owner,
        data={"product_name": "保温杯", "count": "1", "use_ai": "false"},
        files={"image": (filename, b"persistent-image", "image/png")})
    assert generated.status_code == 200, generated.text
    history_id = generated.json()["history_id"]
    assert history_id is not None
    assert set(Path(storage.settings.UPLOAD_DIR).iterdir()) == files_before
    # 每次读取使用新的存储客户端，文件仍从远程存储获取。
    read = service.get(f"/api/prompts/history/{history_id}/image", headers=owner)
    assert read.status_code == 200
    assert read.content == b"persistent-image"
    assert "filename*=UTF-8''" in read.headers["content-disposition"]
    assert service.get(f"/api/prompts/history/{history_id}/image", headers=stranger).status_code == 404
    assert len(objects) == 1


def test_s3_failure_does_not_fall_back_to_temporary_disk(service, monkeypatch):
    from botocore.exceptions import ClientError
    from fastapi import HTTPException
    from app import storage

    monkeypatch.setattr(storage.settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(storage.settings, "S3_BUCKET", "test-uploads")
    failed = ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
    monkeypatch.setattr(storage, "_s3_client", lambda: Mock(put_object=Mock(side_effect=failed)))
    with pytest.raises(HTTPException) as error:
        asyncio.run(storage.save_uploaded_file(b"test", "test.png", "image/png"))
    assert error.value.status_code == 503


def test_local_metadata_cannot_read_outside_upload_folder(service, tmp_path):
    from fastapi import HTTPException
    from app.storage import uploaded_file_response

    path = tmp_path / "outside.txt"
    path.write_text("private")
    with pytest.raises(HTTPException) as error:
        asyncio.run(uploaded_file_response({"file_path": str(path)}))
    assert error.value.status_code == 404


def test_neon_s3_sdk_configuration_and_requests(service, monkeypatch):
    import io
    from botocore.response import StreamingBody
    from botocore.stub import Stubber, ANY
    from app import storage

    for key, value in {
        "STORAGE_BACKEND": "s3", "S3_BUCKET": "test-uploads",
        "AWS_ENDPOINT_URL_S3": "https://storage.example.com", "AWS_REGION": "ap-southeast-1",
        "AWS_ACCESS_KEY_ID": "test-key", "AWS_SECRET_ACCESS_KEY": "test-secret",
    }.items():
        monkeypatch.setattr(storage.settings, key, value)
    storage._s3_client.cache_clear()
    client = storage._s3_client()
    assert client.meta.config.s3["addressing_style"] == "path"
    assert client.meta.config.signature_version == "s3v4"
    try:
        with Stubber(client) as stub:
            stub.add_response("head_bucket", {}, {"Bucket": "test-uploads"})
            stub.add_response("put_object", {}, {
                "Bucket": "test-uploads", "Key": ANY, "Body": b"stored", "ContentType": "image/png",
            })
            asyncio.run(storage.check_storage())
            meta = asyncio.run(storage.save_uploaded_file(b"stored", "中文.png", "image/png"))
            body = StreamingBody(io.BytesIO(b"stored"), 6)
            stub.add_response("get_object", {"Body": body, "ContentLength": 6}, {
                "Bucket": "test-uploads", "Key": meta["key"],
            })

            async def read():
                response = await storage.uploaded_file_response(meta)
                chunks = [chunk async for chunk in response.body_iterator]
                assert b"".join(chunks) == b"stored"

            asyncio.run(read())
            stub.assert_no_pending_responses()
    finally:
        client.close()
        storage._s3_client.cache_clear()


def test_database_files_persist_and_history_does_not_load_blobs(service, monkeypatch):
    from pathlib import Path
    from sqlalchemy import inspect
    from app import storage, models

    monkeypatch.setattr(storage.settings, "STORAGE_BACKEND", "database")
    owner = register(service, "database-owner")
    stranger = register(service, "database-stranger")
    files_before = set(Path(storage.settings.UPLOAD_DIR).iterdir())
    generated = service.post("/api/prompts/generate", headers=owner,
        data={"product_name": "保温杯", "count": "1", "use_ai": "false"},
        files={"image": ("产品图.png", b"db-image", "image/png"), "video": ("参考.mp4", b"db-video", "video/mp4")})
    assert generated.status_code == 200, generated.text
    history_id = generated.json()["history_id"]
    assert history_id is not None
    assert set(Path(storage.settings.UPLOAD_DIR).iterdir()) == files_before
    for media, content in [("image", b"db-image"), ("video", b"db-video")]:
        url = f"/api/prompts/history/{history_id}/{media}"
        assert service.get(url, headers=owner).content == content
        assert service.get(url, headers=stranger).status_code == 404
    history = service.get("/api/prompts/history", headers=owner)
    assert history.status_code == 200
    assert history.json()["items"][0]["id"] == history_id
    assert inspect(models.PromptHistory).attrs.video_data.deferred
    assert inspect(models.PromptHistory).attrs.image_data.deferred
