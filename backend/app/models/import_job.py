"""年报导入任务 ORM。"""
from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ImportJob(Base, TimestampMixin):
    """公开财报导入任务：保存文件路径、解析草稿与状态。"""

    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="pdf_upload")
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="uploaded", index=True
    )
    # uploaded / parsing / mapped / review / committed / failed

    company_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_code_hint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    report_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accounting_standard: Mapped[str | None] = mapped_column(String(30), nullable=True)
    unit_scale: Mapped[float | None] = mapped_column(Float, nullable=True)
    scope: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # AUTO_COMMIT_CANDIDATE / REVIEW_REQUIRED / REJECT_OR_MANUAL

    company_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON 文本：原始抽取 / 映射草稿 / 覆盖率 / 问题列表
    raw_extract_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    mapped_draft_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    coverage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    unmapped_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
