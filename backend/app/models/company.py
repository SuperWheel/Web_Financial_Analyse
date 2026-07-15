"""企业（Company）ORM 模型。"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    """企业档案。三大报表通过 company_id 关联到此。"""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="企业名称")
    code: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, comment="股票代码/统一编号"
    )
    industry: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="所属行业"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Company id={self.id} name={self.name!r}>"
