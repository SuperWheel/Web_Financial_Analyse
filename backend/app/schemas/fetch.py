"""在线拉取年报 API 模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class StockSecurity(BaseModel):
    code: str
    name: str | None = None
    org_id: str | None = None
    category: str | None = None
    type: str | None = None
    column: str | None = None
    industry: str | None = None

class FetchFromUrlRequest(BaseModel):
    url: str = Field(..., min_length=8, description="PDF 直链")
    company_id: int | None = None
    filename: str | None = None


class CninfoDownloadRequest(BaseModel):
    pdf_url: str = Field(..., min_length=8)
    code: str | None = None
    title: str | None = None
    year: int | None = Field(default=None, ge=1990, le=2100)
    name: str | None = None
    company_id: int | None = None


class FilingCandidate(BaseModel):
    source: str = "cninfo"
    code: str
    name: str | None = None
    org_id: str | None = None
    year: int
    title: str
    announce_date: str | None = None
    announcement_id: str | None = None
    adjunct_url: str | None = None
    pdf_url: str


class CninfoMultiSearchRequest(BaseModel):
    """统一多年检索（1 个年份=单年，多个=多年）。"""

    q: str | None = Field(default=None, min_length=1)
    code: str | None = Field(default=None, min_length=1)
    years: list[int] = Field(..., min_length=1, max_length=12)


class CninfoBatchRequest(BaseModel):
    """巨潮多年份批量下载。"""

    q: str | None = Field(default=None, min_length=1, description="证券代码或公司名称")
    code: str | None = Field(
        default=None, min_length=1, description="兼容旧参数，等同 q"
    )
    years: list[int] = Field(
        ...,
        min_length=1,
        max_length=12,
        description="报告年份列表（1–12 个，将去重升序）",
    )
    company_id: int | None = None


class CninfoBatchYearResult(BaseModel):
    year: int
    status: str  # ok | empty | error
    title: str | None = None
    pdf_url: str | None = None
    job_id: int | None = None
    detail: str | None = None


class CninfoBatchSummary(BaseModel):
    ok: int = 0
    empty: int = 0
    error: int = 0


class CninfoBatchResponse(BaseModel):
    code: str
    name: str | None = None
    company_id: int | None = None
    years_requested: list[int]
    summary: CninfoBatchSummary
    results: list[CninfoBatchYearResult]
