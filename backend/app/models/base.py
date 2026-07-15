"""ORM 基类与公共 mixin。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""


class TimestampMixin:
    """提供 created_at / updated_at 的时间戳 mixin。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


# 导出 Base 供 database.create_all 与 alembic（未来）使用
__all__ = ["Base", "TimestampMixin"]
