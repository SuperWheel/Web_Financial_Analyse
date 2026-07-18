"""拉取 PDF 并创建导入任务。"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.services import import_service
from app.services.fetching import cninfo, eastmoney
from app.services.fetching.http_util import FetchError, download_pdf_bytes, ensure_http_url
from app.services.import_service import ImportError

MAX_BATCH_YEARS = 12


def search_cninfo_securities(query: str) -> list[dict[str, Any]]:
    rows = cninfo.search_securities(query)
    # best-effort 补行业（单次检索结果通常很少）
    for row in rows:
        code = str(row.get("code") or "")
        if not code:
            row["industry"] = None
            continue
        try:
            row["industry"] = eastmoney.fetch_industry(code)
        except Exception:  # noqa: BLE001
            row["industry"] = None
    return rows


def search_cninfo_annual(code_or_name: str, year: int) -> list[dict[str, Any]]:
    return cninfo.search_annual_reports(code_or_name, year)


def _normalize_years(years: list[int]) -> list[int]:
    cleaned: list[int] = []
    seen: set[int] = set()
    for y in years or []:
        try:
            yi = int(y)
        except (TypeError, ValueError) as exc:
            raise FetchError(f"非法年份：{y}") from exc
        if yi < 1990 or yi > 2100:
            raise FetchError(f"年份超出范围：{yi}")
        if yi not in seen:
            seen.add(yi)
            cleaned.append(yi)
    cleaned.sort()
    if not cleaned:
        raise FetchError("请至少指定一个年份")
    if len(cleaned) > MAX_BATCH_YEARS:
        raise FetchError(f"单次最多 {MAX_BATCH_YEARS} 个年份")
    return cleaned


def search_cninfo_annual_years(
    code_or_name: str, years: list[int]
) -> list[dict[str, Any]]:
    """多年份检索年报全文；按年升序拼接各年候选。"""
    cleaned = _normalize_years(years)
    out: list[dict[str, Any]] = []
    for year in cleaned:
        try:
            out.extend(cninfo.search_annual_reports(code_or_name, year))
        except FetchError:
            # 单年检索失败：跳过，前端靠 empty 列表提示
            continue
    return out


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



def batch_cninfo_download(
    db: Session,
    *,
    q: str,
    years: list[int],
    company_id: int | None = None,
) -> dict[str, Any]:
    """多年份串行检索+下载；单年失败不中断。不自动 commit。"""
    key = (q or "").strip()
    if not key:
        raise FetchError("请提供证券代码或公司名称")

    cleaned = _normalize_years(years)

    stocks = cninfo.search_securities(key)
    if not stocks:
        raise FetchError(f"未找到证券：{key}")
    stock = stocks[0]
    code = str(stock.get("code") or "").strip()
    name = stock.get("name")
    if not code:
        raise FetchError("证券代码解析失败")

    results: list[dict[str, Any]] = []
    n_ok = n_empty = n_err = 0

    for year in cleaned:
        try:
            candidates = cninfo.search_annual_reports(code, year)
        except FetchError as exc:
            results.append(
                {
                    "year": year,
                    "status": "error",
                    "title": None,
                    "pdf_url": None,
                    "job_id": None,
                    "detail": str(exc.detail if hasattr(exc, "detail") else exc),
                }
            )
            n_err += 1
            continue
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "year": year,
                    "status": "error",
                    "title": None,
                    "pdf_url": None,
                    "job_id": None,
                    "detail": f"检索失败：{exc}",
                }
            )
            n_err += 1
            continue

        if not candidates:
            results.append(
                {
                    "year": year,
                    "status": "empty",
                    "title": None,
                    "pdf_url": None,
                    "job_id": None,
                    "detail": f"未找到 {code} {year} 年年度报告全文",
                }
            )
            n_empty += 1
            continue

        top = candidates[0]
        title = top.get("title")
        pdf_url = top.get("pdf_url")
        try:
            job = create_job_from_cninfo_candidate(
                db,
                pdf_url=str(pdf_url),
                code=code,
                title=str(title) if title else None,
                year=year,
                name=str(name) if name else (top.get("name") or None),
                company_id=company_id,
            )
            results.append(
                {
                    "year": year,
                    "status": "ok",
                    "title": title,
                    "pdf_url": pdf_url,
                    "job_id": getattr(job, "id", None),
                    "detail": None,
                }
            )
            n_ok += 1
        except (FetchError, ImportError) as exc:
            detail = getattr(exc, "detail", None) or str(exc)
            results.append(
                {
                    "year": year,
                    "status": "error",
                    "title": title,
                    "pdf_url": pdf_url,
                    "job_id": None,
                    "detail": str(detail),
                }
            )
            n_err += 1
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "year": year,
                    "status": "error",
                    "title": title,
                    "pdf_url": pdf_url,
                    "job_id": None,
                    "detail": f"下载/建任务失败：{exc}",
                }
            )
            n_err += 1

    return {
        "code": code,
        "name": name,
        "company_id": company_id,
        "years_requested": cleaned,
        "summary": {"ok": n_ok, "empty": n_empty, "error": n_err},
        "results": results,
    }
