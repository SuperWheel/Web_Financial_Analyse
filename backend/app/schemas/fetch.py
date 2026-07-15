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
