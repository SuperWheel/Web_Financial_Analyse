"""数据库基础设施：engine 与 Session。

所有业务层通过依赖注入获取 Session，见 api/deps.py。
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_URL
from app.models.base import Base

# SQLite 需要关闭线程检查，FastAPI 多线程访问时才不会报错
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话的生成器，用作 FastAPI 依赖。

    用完即关，发生异常也保证回滚与关闭。
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_sqlite_columns(bind: Engine | None = None) -> list[str]:
    """为已存在的 SQLite 表补齐 ORM 新增的可空列。

    create_all 不会 ALTER 已有表；开发期扩科目字段时靠本函数增列。
    仅处理 SQLite；返回实际执行的 ALTER 语句列表。
    """
    eng = bind or engine
    if eng.dialect.name != "sqlite":
        return []

    inspector = inspect(eng)
    applied: list[str] = []
    with eng.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                # SQLite ADD COLUMN 仅支持有限语法；科目字段均为可空 Numeric/Integer/String
                col_type = column.type.compile(dialect=eng.dialect)
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'
                conn.execute(text(ddl))
                applied.append(ddl)
    return applied
