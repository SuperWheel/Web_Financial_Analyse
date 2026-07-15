"""Excel 模板下载与三表导入。"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.constants import PERIOD_ANNUAL, PERIOD_QUARTERLY
from app.schemas.excel_import import ExcelImportPreview, ExcelImportResult
from app.services import excel_import_service
from app.services.exceptions import NotFoundError, ServiceError
from app.services.excel_import_service import ValidationError

router = APIRouter(tags=["Excel 导入导出"])


def _to_http(exc: ServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _parse_years(years: str | None) -> list[int] | None:
    if not years:
        return None
    out: list[int] = []
    for part in years.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail=f"years 含非法值: {part}"
            ) from exc
    return out or None


@router.get("/excel/template.xlsx")
def download_excel_template(
    period_type: str = Query(PERIOD_ANNUAL),
    years: str | None = Query(None, description="逗号分隔年份，默认近三年"),
) -> Response:
    """下载空三表模板（可填金额后导入）。"""
    if period_type not in (PERIOD_ANNUAL, PERIOD_QUARTERLY):
        raise HTTPException(
            status_code=422, detail="period_type 须为 annual 或 quarterly"
        )
    try:
        content, filename = excel_import_service.build_template_workbook(
            period_type=period_type,
            years=_parse_years(years),
        )
    except ValidationError as exc:
        raise _to_http(exc)

    quoted = quote(filename)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"template.xlsx\"; filename*=UTF-8''{quoted}"
            )
        },
    )


@router.post(
    "/companies/{company_id}/excel/preview",
    response_model=ExcelImportPreview,
)
async def preview_excel_import(
    company_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
) -> ExcelImportPreview:
    """解析上传 Excel，返回将创建/覆盖的期间预览（不入库）。"""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="空文件")
    try:
        data = excel_import_service.preview_excel_import(db, company_id, content)
    except NotFoundError as exc:
        raise _to_http(exc)
    except ValidationError as exc:
        raise _to_http(exc)
    return ExcelImportPreview.model_validate(data)


@router.post(
    "/companies/{company_id}/excel/import",
    response_model=ExcelImportResult,
)
async def commit_excel_import(
    company_id: int,
    file: UploadFile = File(...),
    overwrite: bool = Form(True),
    db: Session = Depends(get_session),
) -> ExcelImportResult:
    """解析并入库三表；忽略财务比率 sheet。"""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="空文件")
    try:
        data = excel_import_service.commit_excel_import(
            db, company_id, content, overwrite=overwrite
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    except ValidationError as exc:
        raise _to_http(exc)
    return ExcelImportResult.model_validate(data)
