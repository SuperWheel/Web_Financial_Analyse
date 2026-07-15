"""Excel 导出路由：三表 + 财务比率。"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.constants import PERIOD_ANNUAL, PERIOD_QUARTERLY
from app.services import export_service
from app.services.exceptions import NotFoundError, ServiceError
from app.services.export_service import ValidationError

router = APIRouter(prefix="/companies/{company_id}", tags=["导出"])


def _to_http(exc: ServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/export.xlsx")
def export_excel(
    company_id: int,
    period_type: str = Query(PERIOD_ANNUAL),
    years: str | None = Query(
        None, description="逗号分隔年份过滤，如 2023,2024,2025"
    ),
    db: Session = Depends(get_session),
) -> Response:
    """导出企业三表与财务比率为 Excel 工作簿。"""
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
        content, filename = export_service.build_export_workbook(
            db,
            company_id,
            period_type=period_type,
            years=year_list,
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    except ValidationError as exc:
        raise _to_http(exc)

    # RFC 5987 文件名，兼容中文
    quoted = quote(filename)
    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"export.xlsx\"; filename*=UTF-8''{quoted}"
        ),
    }
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers=headers,
    )
