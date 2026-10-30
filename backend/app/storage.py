"""本地开发存磁盘；云端使用 PostgreSQL 或私有 S3 兼容存储。"""
import asyncio
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException
from fastapi.responses import FileResponse, StreamingResponse, Response

from app.config import settings


def validate_storage_config():
    if settings.STORAGE_BACKEND not in {"local", "database", "s3"}:
        raise ValueError("STORAGE_BACKEND 必须为 local、database 或 s3")
    if settings.STORAGE_BACKEND == "s3":
        required = ("S3_BUCKET", "AWS_ENDPOINT_URL_S3", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
        missing = [name for name in required if not getattr(settings, name)]
        if missing:
            raise ValueError(f"对象存储配置缺失：{', '.join(missing)}")
        if not settings.AWS_ENDPOINT_URL_S3.startswith("https://"):
            raise ValueError("对象存储端点必须使用 HTTPS")


@lru_cache(maxsize=1)
def _s3_client():
    import boto3
    from botocore.config import Config

    validate_storage_config()
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT_URL_S3,
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=30,
            retries={"mode": "standard", "max_attempts": 2},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


async def check_storage():
    validate_storage_config()
    if settings.STORAGE_BACKEND == "s3":
        await asyncio.to_thread(_s3_client().head_bucket, Bucket=settings.S3_BUCKET)
    elif settings.STORAGE_BACKEND == "local":
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


async def save_uploaded_file(file_bytes: bytes, filename: str, content_type: str) -> dict:
    file_id = uuid4().hex
    # 对象键不使用用户提供的路径，文件名只作为显示元数据保存。
    meta = {"file_id": file_id, "filename": filename, "content_type": content_type, "size": len(file_bytes)}
    if settings.STORAGE_BACKEND == "database":
        # 二进制内容由生成接口与历史记录在同一个数据库事务中保存。
        meta.update(storage="database")
    elif settings.STORAGE_BACKEND == "s3":
        key = f"uploads/{file_id}"
        try:
            await asyncio.to_thread(
                _s3_client().put_object,
                Bucket=settings.S3_BUCKET, Key=key, Body=file_bytes, ContentType=content_type,
            )
        except (BotoCoreError, ClientError):
            raise HTTPException(status_code=503, detail="素材存储暂时不可用，请稍后重试")
        meta.update(storage="s3", bucket=settings.S3_BUCKET, key=key)
    else:
        folder = Path(settings.UPLOAD_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / file_id
        await asyncio.to_thread(path.write_bytes, file_bytes)
        meta.update(storage="local", file_path=str(path))
    return meta


def _stream_body(body):
    try:
        yield from body.iter_chunks(chunk_size=1024 * 1024)
    finally:
        body.close()


async def uploaded_file_response(meta: dict, content=None):
    filename = meta.get("filename") or "file"
    content_type = meta.get("content_type") or "application/octet-stream"
    if meta.get("storage") == "database":
        if content is None:
            raise HTTPException(status_code=404, detail="素材文件不存在")
        return Response(content=content, media_type=content_type, headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename, safe='')}"
        })
    if meta.get("storage") == "s3":
        if settings.STORAGE_BACKEND != "s3" or meta.get("bucket") != settings.S3_BUCKET:
            raise HTTPException(status_code=503, detail="素材存储配置不匹配，请联系管理员")
        try:
            result = await asyncio.to_thread(
                _s3_client().get_object, Bucket=settings.S3_BUCKET, Key=meta["key"],
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise HTTPException(status_code=404, detail="素材文件不存在")
            raise HTTPException(status_code=503, detail="素材读取暂时不可用，请稍后重试")
        except BotoCoreError:
            raise HTTPException(status_code=503, detail="素材读取暂时不可用，请稍后重试")
        headers = {"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename, safe='')}"}
        if result.get("ContentLength") is not None:
            headers["Content-Length"] = str(result["ContentLength"])
        return StreamingResponse(_stream_body(result["Body"]), media_type=content_type, headers=headers)

    # 兼容旧版本的本地元数据；仅允许读取配置的上传目录。
    folder = Path(settings.UPLOAD_DIR).resolve()
    path = Path(meta.get("file_path") or "").resolve()
    if not path.is_relative_to(folder) or not path.is_file():
        raise HTTPException(status_code=404, detail="素材文件不存在或原临时文件已过期")
    return FileResponse(path, media_type=content_type, filename=filename, content_disposition_type="inline")
