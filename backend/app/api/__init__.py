"""路由汇总。

新增领域路由：在这里 include 进 api_router，并在 main.py 挂载一次。
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.companies import router as companies_router
from app.api.compare import router as compare_router
from app.api.imports import router as imports_router
from app.api.export import router as export_router
from app.api.excel_io import router as excel_io_router
from app.api.fetch import router as fetch_router
from app.api.ratios import router as ratios_router
from app.api.statements import router as statements_router

api_router = APIRouter()
api_router.include_router(companies_router)
api_router.include_router(statements_router)
api_router.include_router(imports_router)
api_router.include_router(ratios_router)
api_router.include_router(compare_router)
api_router.include_router(export_router)
api_router.include_router(excel_io_router)
api_router.include_router(fetch_router)

__all__ = ["api_router"]
