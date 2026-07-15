"""年报披露明细行（L0）：导入原文科目行 + 映射关系。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StatementDisclosureLine(Base):
    """披露明细：一行 = 年报中的一个科目行（或导入草稿行）。"""

    __tablename__ = "statement_disclosure_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statement_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="balance|income|cashflow"
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="import", comment="import|manual"
    )
    import_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    line_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label_raw: Mapped[str] = mapped_column(String(512), nullable=False)
    label_norm: Mapped[str | None] = mapped_column(String(512), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    unit_scale_applied: Mapped[float | None] = mapped_column(Float, nullable=True, default=1.0)
    role: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="detail|subtotal|total|header|unknown"
    )
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mapped_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    map_rule: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="alias|rollup|manual|none"
    )
    map_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    include_in_aggregate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
