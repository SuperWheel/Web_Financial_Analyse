"""拉取 PDF 并创建导入任务。"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.services import import_service
from app.services.fetching import cninfo
from app.services.fetching.http_util import FetchError, download_pdf_bytes, ensure_http_url
from app.services.import_service import ImportError


def search_cninfo_securities(query: str) -> list[dict[str, Any]]:
    return cninfo.search_securities(query)


def search_cninfo_annual(code_or_name: str, year: int) -> list[dict[str, Any]]:
    return cninfo.search_annual_reports(code_or_name, year)


def create_job_from_pdf_url(
    db: Session,
    *,
    url: str,
    company_id: int | None = None,
    filename: str | None = None,
    source_type: str = "pdf_url",
    company_code_hint: str | None = None,
    company_hint: str | None = None,
    report_year: int | None = None,
) -> Any:
    ensure_http_url(url)
    try:
        content, name_hint = download_pdf_bytes(
            url,
            referer="https://www.cninfo.com.cn/",
        )
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise FetchError(f"下载失败：{exc}") from exc

    fname = filename or name_hint
    if not fname.lower().endswith(".pdf"):
        fname = f"{fname}.pdf"
    # 净化文件名
    fname = fname.replace("/", "_").replace("\\", "_")[:200]

    try:
        job = import_service.create_job_from_upload(
            db,
            filename=fname,
            content=content,
            source_type=source_type,
            company_id=company_id,
            company_code_hint=company_code_hint,
            company_hint=company_hint,
            report_year=report_year,
        )
    except ImportError:
        raise
    return job


def create_job_from_cninfo_candidate(
    db: Session,
    *,
    pdf_url: str,
    code: str | None = None,
    title: str | None = None,
    year: int | None = None,
    name: str | None = None,
    company_id: int | None = None,
) -> Any:
    host = urlparse(pdf_url).netloc.lower()
    if "cninfo.com.cn" not in host and "static.cninfo" not in host:
        # 仍允许，但标记 source
        pass
    safe_title = (title or "annual_report").replace("/", "_")[:80]
    code_part = code or "stock"
    year_part = str(year) if year else "year"
    fname = f"{code_part}_{year_part}_{safe_title}.pdf"
    return create_job_from_pdf_url(
        db,
        url=pdf_url,
        company_id=company_id,
        filename=fname,
        source_type="pdf_cninfo",
        company_code_hint=code,
        company_hint=name,
        report_year=year,
    )
