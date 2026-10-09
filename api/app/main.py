from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.permissions import sync_permission_catalog
from app.core.storage import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # 幂等补齐内置权限清单（只新增缺失项），保证权限管理页始终能看到完整能力字典
    async with AsyncSessionLocal() as db:
        await sync_permission_catalog(db)
    await storage.ensure_bucket()
    yield


app = FastAPI(
    title=settings.app_name,
    description="医药销售管理系统 API（全异步 FastAPI）",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": "数据校验失败：可能存在重复记录或关联数据不存在"},
    )


@app.get("/", tags=["健康检查"], summary="服务健康检查")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
