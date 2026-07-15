"""财务比率路由：只读计算，无落库。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.constants import PERIOD_ANNUAL, PERIOD_QUARTERLY, QUARTERS
from app.schemas.ratio import RatioHistory, RatioPeriod, RatioSnapshot
from app.services import ratio_service
from app.services.exceptions import NotFoundError, ServiceError

router = APIRouter(prefix="/companies/{company_id}", tags=["财务比率"])


def _to_http(exc: ServiceError):
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _validate_period(period_type: str, quarter: int | None) -> int | None:
    if period_type not in (PERIOD_ANNUAL, PERIOD_QUARTERLY):
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="period_type 须为 annual 或 quarterly")
    if period_type == PERIOD_ANNUAL:
        return None
    if quarter is None or quarter not in QUARTERS:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="季报必须提供 quarter（1-4）")
    return quarter


@router.get("/ratio-periods", response_model=list[RatioPeriod])
def get_ratio_periods(
    company_id: int, db: Session = Depends(get_session)
) -> list[RatioPeriod]:
    """列出企业有报表数据的报告期。"""
    try:
        rows = ratio_service.list_ratio_periods(db, company_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return [RatioPeriod.model_validate(r) for r in rows]


@router.get("/ratios", response_model=RatioSnapshot)
def get_ratios(
    company_id: int,
    year: int = Query(..., ge=1990, le=2100),
    period_type: str = Query("annual"),
    quarter: int | None = Query(None),
    db: Session = Depends(get_session),
) -> RatioSnapshot:
    """计算指定报告期的财务比率。"""
    q = _validate_period(period_type, quarter)
    try:
        data = ratio_service.compute_period_ratios(
            db, company_id, year=year, period_type=period_type, quarter=q
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    return RatioSnapshot.model_validate(data)


@router.get("/ratios/history", response_model=RatioHistory)
def get_ratio_history(
    company_id: int,
    period_type: str = Query("annual"),
    keys: str | None = Query(
        None, description="逗号分隔比率 key；默认全部"
    ),
    db: Session = Depends(get_session),
) -> RatioHistory:
    """多期比率序列（图表）。"""
    if period_type not in (PERIOD_ANNUAL, PERIOD_QUARTERLY):
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="period_type 须为 annual 或 quarterly")
    key_list = [k.strip() for k in keys.split(",") if k.strip()] if keys else None
    try:
        data = ratio_service.compute_ratio_history(
            db, company_id, period_type=period_type, keys=key_list
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    return RatioHistory.model_validate(data)
