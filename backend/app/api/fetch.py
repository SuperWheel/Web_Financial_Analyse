"""年报在线拉取：URL 直下 + 巨潮检索下载。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.fetch import (
    CninfoBatchRequest,
    CninfoBatchResponse,
    CninfoDownloadRequest,
    CninfoMultiSearchRequest,
    FetchFromUrlRequest,
    FilingCandidate,
    StockSecurity,
)
from app.schemas.import_job import ImportJobRead
from app.services import import_service
from app.services.exceptions import ServiceError
from app.services.fetching import service as fetch_service
from app.services.fetching.http_util import FetchError
from app.services.import_service import ImportError

router = APIRouter(prefix="/imports/fetch", tags=["年报拉取"])


def _to_http(exc: ServiceError):
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/cninfo/securities", response_model=list[StockSecurity])
def cninfo_securities(
    q: str = Query(..., min_length=1, description="证券代码或公司名称"),
) -> list[StockSecurity]:
    """按代码/名称检索证券列表（支持全称回退简称）。"""
    try:
        rows = fetch_service.search_cninfo_securities(q)
    except FetchError as exc:
        raise _to_http(exc)
    return [StockSecurity.model_validate(r) for r in rows]


@router.get("/cninfo/search", response_model=list[FilingCandidate])
def cninfo_search(
    year: int = Query(..., ge=1990, le=2100),
    q: str | None = Query(
        None, min_length=1, description="证券代码或公司名称（推荐）"
    ),
    code: str | None = Query(
        None, min_length=1, description="兼容旧参数，等同 q"
    ),
) -> list[FilingCandidate]:
    """巨潮检索指定年份年度报告（全文）候选。支持代码或公司名称。"""
    key = (q or code or "").strip()
    if not key:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="请提供 q 或 code（代码/名称）")
    try:
        rows = fetch_service.search_cninfo_annual(key, year)
    except FetchError as exc:
        raise _to_http(exc)
    return [FilingCandidate.model_validate(r) for r in rows]


@router.post("/cninfo/search-years", response_model=list[FilingCandidate])
def cninfo_search_years(payload: CninfoMultiSearchRequest) -> list[FilingCandidate]:
    """多年份检索年报全文候选（不下载）。1 年=单年，多年=拼接列表。"""
    key = (payload.q or payload.code or "").strip()
    if not key:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="请提供 q 或 code（代码/名称）")
    try:
        rows = fetch_service.search_cninfo_annual_years(key, list(payload.years))
    except FetchError as exc:
        raise _to_http(exc)
    return [FilingCandidate.model_validate(r) for r in rows]


@router.post(
    "/from-url",
    response_model=ImportJobRead,
    status_code=status.HTTP_201_CREATED,
)
def fetch_from_url(
    payload: FetchFromUrlRequest, db: Session = Depends(get_session)
) -> ImportJobRead:
    """从 PDF URL 下载并创建导入任务（不自动入库）。"""
    try:
        job = fetch_service.create_job_from_pdf_url(
            db,
            url=payload.url,
            company_id=payload.company_id,
            filename=payload.filename,
            source_type="pdf_url",
        )
    except (FetchError, ImportError) as exc:
        raise _to_http(exc)
    return ImportJobRead.model_validate(import_service.job_to_dict(job))


@router.post(
    "/cninfo/download",
    response_model=ImportJobRead,
    status_code=status.HTTP_201_CREATED,
)
def cninfo_download(
    payload: CninfoDownloadRequest, db: Session = Depends(get_session)
) -> ImportJobRead:
    """下载巨潮候选 PDF 并创建导入任务。"""
    try:
        job = fetch_service.create_job_from_cninfo_candidate(
            db,
            pdf_url=payload.pdf_url,
            code=payload.code,
            title=payload.title,
            year=payload.year,
            name=payload.name,
            company_id=payload.company_id,
        )
    except (FetchError, ImportError) as exc:
        raise _to_http(exc)
    return ImportJobRead.model_validate(import_service.job_to_dict(job))


@router.post(
    "/cninfo/batch",
    response_model=CninfoBatchResponse,
    status_code=status.HTTP_200_OK,
)
def cninfo_batch(
    payload: CninfoBatchRequest, db: Session = Depends(get_session)
) -> CninfoBatchResponse:
    """多年份串行检索下载；单年失败不中断；不自动入库。"""
    key = (payload.q or payload.code or "").strip()
    if not key:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="请提供 q 或 code（代码/名称）")
    try:
        data = fetch_service.batch_cninfo_download(
            db,
            q=key,
            years=list(payload.years),
            company_id=payload.company_id,
        )
    except FetchError as exc:
        raise _to_http(exc)
    return CninfoBatchResponse.model_validate(data)
