from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，支持环境变量 / .env 文件覆盖。"""

    app_name: str = "medsales-api"
    debug: bool = True
    api_prefix: str = "/api"

    database_url: str = (
        "postgresql+asyncpg://postgres:pass01!@127.0.0.1:5688/medsalesdb"
    )

    jwt_secret: str = "medsales-change-me-to-a-long-random-secret-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # 系统间对接 API Key（逗号分隔支持多个，轮换期间可同时配置新旧两个）
    sys_api_keys: str = ""

    cors_origins: str = "*"

    # 对象存储（MinIO / S3 兼容），用于 GSP 证照扫描件等文件归档
    s3_endpoint_url: str = "http://127.0.0.1:9020"
    s3_access_key: str = "medsales"
    s3_secret_key: str = "medsales-minio-secret"
    s3_bucket: str = "medsales"
    s3_region: str = "us-east-1"
    s3_presign_expire_seconds: int = 3600

    # GSP 交易准入校验
    # 开启后，已建立首营资质档案（即已录入证照）的客户/供应商/商品在交易前会被校验：
    # 存在过期、已驳回或待审核的证照时禁止下单/收货。
    gsp_enforce_qualification: bool = True
    # 严格模式：未建立任何资质档案的主体同样禁止交易（存量数据默认不启用）
    gsp_strict_qualification: bool = False
    # 证照「即将到期」预警阈值（天）
    gsp_expiry_warning_days: int = 90

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sys_api_key_list(self) -> list[str]:
        return [k.strip() for k in self.sys_api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
