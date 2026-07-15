"""FastAPI 依赖。"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import get_db


def get_session() -> Generator[Session, None, None]:
    """数据库会话依赖（薄封装，便于未来扩展）。"""
    yield from get_db()
