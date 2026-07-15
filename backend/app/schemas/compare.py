"""多期科目对比 API 响应模型。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ComparePeriodMeta(BaseModel):
    year: int
    period_type: Literal["annual", "quarterly"]
    quarter: int | None = None
    label: str
    statement_id: int | None = None


class CompareFieldRow(BaseModel):
    key: str
    label: str
    values: list[float | None]
    deltas: list[float | None]
    delta_pcts: list[float | None]
    structure_pcts: list[float | None]


class CompareGroup(BaseModel):
    key: str
    label: str
    rows: list[CompareFieldRow] = Field(default_factory=list)


class CompareMatrix(BaseModel):
    company_id: int
    statement_type: Literal["balance", "income", "cashflow"]
    period_type: Literal["annual", "quarterly"]
    base_field: str | None = None
    base_label: str | None = None
    periods: list[ComparePeriodMeta]
    groups: list[CompareGroup]


# 期间列表复用比率侧结构（字段一致）
class ComparePeriod(BaseModel):
    year: int
    period_type: Literal["annual", "quarterly"]
    quarter: int | None = None
    has_balance: bool = False
    has_income: bool = False
    has_cashflow: bool = False
