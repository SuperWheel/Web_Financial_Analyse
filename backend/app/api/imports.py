"""公开财报导入路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.import_job import ImportCommitRequest, ImportJobRead, ImportJobUpdate
from app.services import import_service
from app.services.exceptions import NotFoundError, ServiceError
from app.services.import_service import ImportError

router = APIRouter(prefix="/imports/filings", tags=["年报导入"])


def _to_http(exc: ServiceError):
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("", response_model=list[ImportJobRead])
def list_import_jobs(db: Session = Depends(get_session)) -> list[ImportJobRead]:
    jobs = import_service.list_jobs(db)
    return [ImportJobRead.model_validate(import_service.job_to_dict(j)) for j in jobs]


@router.post("", response_model=ImportJobRead, status_code=status.HTTP_201_CREATED)
async def upload_filing(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
) -> ImportJobRead:
    content = await file.read()
    try:
        job = import_service.create_job_from_upload(
            db, filename=file.filename or "upload.pdf", content=content
        )
    except ImportError as exc:
        raise _to_http(exc)
    return ImportJobRead.model_validate(import_service.job_to_dict(job))


@router.get("/{job_id}", response_model=ImportJobRead)
def get_import_job(job_id: int, db: Session = Depends(get_session)) -> ImportJobRead:
    try:
        job = import_service.get_job(db, job_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return ImportJobRead.model_validate(import_service.job_to_dict(job))


@router.patch("/{job_id}", response_model=ImportJobRead)
def update_import_job(
    job_id: int, payload: ImportJobUpdate, db: Session = Depends(get_session)
) -> ImportJobRead:
    try:
        job = import_service.update_job_draft(
            db,
            job_id,
            company_id=payload.company_id,
            company_hint=payload.company_hint,
            company_code_hint=payload.company_code_hint,
            report_year=payload.report_year,
            period_type=payload.period_type,
            quarter=payload.quarter,
            statements=payload.statements,
        )
    except (NotFoundError, ImportError) as exc:
        raise _to_http(exc)
    return ImportJobRead.model_validate(import_service.job_to_dict(job))


@router.post("/{job_id}/commit", response_model=ImportJobRead)
def commit_import_job(
    job_id: int,
    payload: ImportCommitRequest | None = None,
    db: Session = Depends(get_session),
) -> ImportJobRead:
    body = payload or ImportCommitRequest()
    try:
        job = import_service.commit_job(
            db, job_id, company_id=body.company_id, overwrite=body.overwrite
        )
    except (NotFoundError, ImportError) as exc:
        raise _to_http(exc)
    return ImportJobRead.model_validate(import_service.job_to_dict(job))


@router.delete(
    "/{job_id}",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_import_job(job_id: int, db: Session = Depends(get_session)) -> Response:
    try:
        import_service.delete_job(db, job_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
