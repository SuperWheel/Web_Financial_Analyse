"""导入任务 API 模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ImportJobRead(BaseModel):
    id: int
    source_type: str
    original_filename: str
    status: str
    company_hint: str | None = None
    company_code_hint: str | None = None
    company_id: int | None = None
    report_year: int | None = None
    period_type: str | None = None
    quarter: int | None = None
    accounting_standard: str | None = None
    unit_scale: float | None = None
    scope: str | None = None
    confidence: float | None = None
    fill_mode: str | None = None
    error_message: str | None = None
    coverage: dict[str, Any] = Field(default_factory=dict)
    issues: list[Any] = Field(default_factory=list)
    unmapped: list[Any] = Field(default_factory=list)
    draft: dict[str, Any] = Field(default_factory=dict)
    raw_extract: dict[str, Any] = Field(default_factory=dict)
    commit_result: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ImportJobUpdate(BaseModel):
    company_id: int | None = None
    company_hint: str | None = None
    company_code_hint: str | None = None
    report_year: int | None = None
    period_type: str | None = None
    quarter: int | None = None
    statements: dict[str, dict[str, float | None]] | None = None


class ImportCommitRequest(BaseModel):
    company_id: int | None = None
    overwrite: bool = True
