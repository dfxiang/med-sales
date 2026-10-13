"""对象存储（MinIO / S3 兼容）访问封装。

本系统使用独立的 MinIO 实例保存 GSP 合规所需的证照扫描件等文件。
boto3 为同步客户端，这里统一通过线程池调用，避免阻塞事件循环。
"""

from __future__ import annotations

import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)


class ObjectStorage:
    """轻量对象存储客户端（懒加载 + 幂等建桶）。"""

    def __init__(self) -> None:
        self._client = None

    @property
    def bucket(self) -> str:
        return settings.s3_bucket

    def _build_client(self):
        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    async def ensure_bucket(self) -> bool:
        """确保 bucket 存在；失败仅记录告警，不阻塞应用启动。"""

        def _ensure() -> bool:
            client = self.client()
            try:
                client.head_bucket(Bucket=self.bucket)
                return True
            except ClientError:
                try:
                    client.create_bucket(Bucket=self.bucket)
                    return True
                except ClientError as exc:  # pragma: no cover - 依赖真实存储
                    logger.warning("创建对象存储 bucket 失败: %s", exc)
                    return False
            except Exception as exc:  # pragma: no cover - 网络不可达等
                logger.warning("对象存储不可用: %s", exc)
                return False

        return await run_in_threadpool(_ensure)

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> None:
        def _put() -> None:
            extra = {"ContentType": content_type} if content_type else None
            kwargs = {"Bucket": self.bucket, "Key": key, "Body": data}
            if extra:
                kwargs.update(extra)
            self.client().put_object(**kwargs)

        await run_in_threadpool(_put)

    async def get_object(self, key: str) -> bytes:
        def _get() -> bytes:
            resp = self.client().get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()

        return await run_in_threadpool(_get)

    async def get_object_or_none(self, key: str) -> bytes | None:
        """读取对象；对象不存在时返回 None（其它错误照常抛出）。"""

        def _get() -> bytes | None:
            try:
                resp = self.client().get_object(Bucket=self.bucket, Key=key)
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if code in {"NoSuchKey", "404", "NotFound"} or status == 404:
                    return None
                raise
            return resp["Body"].read()

        return await run_in_threadpool(_get)

    async def head_object(self, key: str) -> bool:
        """对象是否存在（不存在返回 False，其它错误照常抛出）。"""

        def _head() -> bool:
            try:
                self.client().head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if code in {"NoSuchKey", "404", "NotFound"} or status == 404:
                    return False
                raise

        return await run_in_threadpool(_head)
    async def delete_object(self, key: str) -> None:
        def _delete() -> None:
            self.client().delete_object(Bucket=self.bucket, Key=key)

        await run_in_threadpool(_delete)

    async def presigned_url(self, key: str, filename: str | None = None) -> str:
        def _sign() -> str:
            params = {"Bucket": self.bucket, "Key": key}
            if filename:
                params["ResponseContentDisposition"] = (
                    "attachment; filename*=UTF-8''" + filename
                )
            return self.client().generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=settings.s3_presign_expire_seconds,
            )

        return await run_in_threadpool(_sign)


storage = ObjectStorage()


def get_storage() -> ObjectStorage:
    """FastAPI 依赖：返回对象存储单例。

    路由通过依赖注入取用（而不是直接 import 模块级 `storage`），单测才能用
    `app.dependency_overrides` 换成内存实现，避免依赖真实 MinIO。
    """
    return storage
