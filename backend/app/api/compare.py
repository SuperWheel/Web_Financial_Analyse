"""多期科目对比路由：只读计算，无落库。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.constants import PERIOD_ANNUAL, PERIOD_QUARTERLY
from app.schemas.compare import CompareMatrix, ComparePeriod
from app.services import compare_service
from app.services.compare_service import ValidationError
from app.services.exceptions import NotFoundError, ServiceError

router = APIRouter(prefix="/companies/{company_id}", tags=["多期对比"])


def _to_http(exc: ServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/compare-periods", response_model=list[ComparePeriod])
def get_compare_periods(
    company_id: int, db: Session = Depends(get_session)
) -> list[ComparePeriod]:
    """列出企业有报表数据的报告期。"""
    try:
        rows = compare_service.list_compare_periods(db, company_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return [ComparePeriod.model_validate(r) for r in rows]


@router.get("/compare", response_model=CompareMatrix)
def get_compare(
    company_id: int,
    statement_type: str = Query(
        ..., description="balance | income | cashflow"
    ),
    period_type: str = Query(PERIOD_ANNUAL),
    years: str | None = Query(
        None, description="逗号分隔年份过滤，如 2023,2024,2025"
    ),
    db: Session = Depends(get_session),
) -> CompareMatrix:
    """科目级多期矩阵（金额 / 环比 / 结构）。"""
    if period_type not in (PERIOD_ANNUAL, PERIOD_QUARTERLY):
        raise HTTPException(
            status_code=422, detail="period_type 须为 annual 或 quarterly"
        )
    year_list: list[int] | None = None
    if years:
        year_list = []
        for part in years.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                year_list.append(int(part))
            except ValueError as exc:
                raise HTTPException(
                    status_code=422, detail=f"years 含非法值: {part}"
                ) from exc
        if not year_list:
            year_list = None

    try:
        data = compare_service.build_compare_matrix(
            db,
            company_id,
            statement_type=statement_type,
            period_type=period_type,
            years=year_list,
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    except ValidationError as exc:
        raise _to_http(exc)
    return CompareMatrix.model_validate(data)
