"""Excel 导入预览 / 结果模型。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExcelPeriodRef(BaseModel):
    year: int
    period_type: Literal["annual", "quarterly"]
    quarter: int | None = None
    label: str


class ExcelSheetPreview(BaseModel):
    statement_type: Literal["balance", "income", "cashflow"]
    label: str
    periods: list[ExcelPeriodRef] = Field(default_factory=list)
    non_null_fields: int = 0
    rows_with_code: int = 0


class ExcelImportPreview(BaseModel):
    company_id: int
    period_type: Literal["annual", "quarterly"] | None = None
    periods: list[ExcelPeriodRef] = Field(default_factory=list)
    sheets: list[ExcelSheetPreview] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    will_create: list[str] = Field(default_factory=list)
    will_update: list[str] = Field(default_factory=list)
    will_skip_empty: list[str] = Field(default_factory=list)


class ExcelImportResult(BaseModel):
    company_id: int
    created: list[str] = Field(default_factory=list)
    updated: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    statement_ids: dict[str, Any] = Field(default_factory=dict)
