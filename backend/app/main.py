"""FastAPI 应用入口。

启动：在 backend/ 目录下执行
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import API_PREFIX, BACKEND_CORS_ORIGINS
from app.database import engine, ensure_sqlite_columns
from app.models import base  # noqa: F401
from app import models as _models  # noqa: F401  注册全部 ORM


@asynccontextmanager
async def lifespan(app: FastAPI):
    base.Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns(engine)
    yield


app = FastAPI(
    title="Web_Financial_Analyse 财务分析系统",
    description="轻量级企业财务报表分析系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS：允许前端 Vite dev server 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{API_PREFIX}/health", tags=["系统"], summary="健康检查")
def health() -> dict[str, str]:
    """健康检查端点。"""
    return {"status": "ok"}


# 挂载业务路由
app.include_router(api_router, prefix=API_PREFIX)
