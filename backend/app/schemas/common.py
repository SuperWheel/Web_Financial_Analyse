"""通用 Pydantic 模型：统一响应包装等。"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Message(BaseModel):
    """简单消息响应。"""

    message: str


class ErrorResponse(BaseModel):
    """标准错误响应。"""

    detail: str


# 保留 Generic 包装能力，便于未来统一响应体（当前 FastAPI 直接返回业务对象）
class PaginatedData(BaseModel, Generic[T]):
    """分页数据包装。Phase 1+ 报表列表可能用到。"""

    items: list[T]
    total: int
