"""财务比率 API 响应模型。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RatioPeriod(BaseModel):
    year: int
    period_type: Literal["annual", "quarterly"]
    quarter: int | None = None
    has_balance: bool = False
    has_income: bool = False
    has_cashflow: bool = False


class RatioItem(BaseModel):
    key: str
    name: str
    group: str
    unit: Literal["ratio", "percent"]
    description: str
    formula: str
    value: float | None = None
    missing: list[str] = Field(default_factory=list)
    reason: str | None = None
    variant: str | None = None


class RatioSnapshot(BaseModel):
    company_id: int
    period: dict[str, Any]
    sources: dict[str, int | None]
    ratios: list[RatioItem]
    summary: dict[str, int]


class RatioHistory(BaseModel):
    company_id: int
    period_type: str
    periods: list[dict[str, Any]]
    series: dict[str, Any]
