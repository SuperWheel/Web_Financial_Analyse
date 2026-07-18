"""年报导入业务：上传、解析、修正、入库。"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import IMPORTS_DIR
from app.models.import_job import ImportJob
from app.schemas.company import CompanyCreate
from app.schemas.statement import (
    BalanceSheetCreate,
    BalanceSheetUpdate,
    CashFlowStatementCreate,
    CashFlowStatementUpdate,
    IncomeStatementCreate,
    IncomeStatementUpdate,
)
from app.services import company_service, disclosure_service, statement_service
from app.services.exceptions import NotFoundError, ServiceError
from app.services.importing.pipeline import run_pipeline_on_path
from app.services.statement_service import ValidationError


class ImportError(ServiceError):
    status_code = 400


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _loads(s: str | None, default: Any = None) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return default


def get_job(db: Session, job_id: int) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if job is None:
        raise NotFoundError(f"导入任务 id={job_id} 不存在")
    return job


def list_jobs(db: Session, limit: int = 50) -> list[ImportJob]:
    from sqlalchemy import select

    stmt = select(ImportJob).order_by(ImportJob.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def create_job_from_upload(
    db: Session,
    *,
    filename: str,
    content: bytes,
    source_type: str = "pdf_upload",
    company_id: int | None = None,
    company_code_hint: str | None = None,
    company_hint: str | None = None,
    report_year: int | None = None,
) -> ImportJob:
    if not filename.lower().endswith(".pdf"):
        raise ImportError("一期仅支持 PDF 文件")
    if not content:
        raise ImportError("空文件")
    if len(content) > 40 * 1024 * 1024:
        raise ImportError("文件过大（>40MB）")

    job_key = uuid.uuid4().hex
    dest_dir = IMPORTS_DIR / job_key
    dest_dir.mkdir(parents=True, exist_ok=True)
    # 保留后缀
    safe_name = Path(filename).name
    dest = dest_dir / safe_name
    dest.write_bytes(content)

    job = ImportJob(
        source_type=source_type or "pdf_upload",
        original_filename=safe_name,
        file_path=str(dest),
        status="parsing",
        company_id=company_id,
        company_code_hint=company_code_hint,
        company_hint=company_hint,
        report_year=report_year,
    )
    # 拉取场景预填提示，解析后按「空则补、有则解析优先」合并
    pref_company_id = company_id
    pref_code = company_code_hint
    pref_name = company_hint
    pref_year = report_year
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        result = run_pipeline_on_path(dest)
        # 元数据合并：
        # - 巨潮/URL 拉取：证券身份以预填为准（解析易被释义表/关联方污染）
        # - 本地上传：解析优先，缺省回退预填
        if (source_type or "") in ("pdf_cninfo", "pdf_url"):
            job.company_hint = pref_name or result.company_hint
            job.company_code_hint = pref_code or result.company_code_hint
            job.report_year = pref_year or result.report_year
        else:
            job.company_hint = result.company_hint or pref_name
            job.company_code_hint = result.company_code_hint or pref_code
            job.report_year = result.report_year or pref_year
        if pref_company_id is not None:
            job.company_id = pref_company_id
        job.period_type = result.period_type
        job.quarter = result.quarter
        job.accounting_standard = result.accounting_standard
        job.unit_scale = result.unit_scale
        job.scope = result.scope
        job.confidence = result.confidence
        job.fill_mode = result.fill_mode
        job.raw_extract_json = _dumps(result.raw_extract)
        job.mapped_draft_json = _dumps(result.to_draft_dict())
        job.coverage_json = _dumps(result.coverage)
        job.issues_json = _dumps(result.issues)
        job.unmapped_json = _dumps(result.unmapped)
        if result.status == "failed":
            job.status = "failed"
            job.error_message = result.error_message
        else:
            job.status = "review"
            job.error_message = None
    except Exception as exc:  # pragma: no cover
        job.status = "failed"
        job.error_message = f"解析异常: {exc}"
    db.commit()
    db.refresh(job)
    return job


def update_job_draft(
    db: Session,
    job_id: int,
    *,
    company_id: int | None = None,
    company_hint: str | None = None,
    company_code_hint: str | None = None,
    report_year: int | None = None,
    period_type: str | None = None,
    quarter: int | None = None,
    statements: dict[str, dict[str, float | None]] | None = None,
) -> ImportJob:
    job = get_job(db, job_id)
    if job.status == "committed":
        raise ImportError("任务已入库，不能修改")
    if company_id is not None:
        company_service.get_company(db, company_id)
        job.company_id = company_id
    if company_hint is not None:
        job.company_hint = company_hint
    if company_code_hint is not None:
        job.company_code_hint = company_code_hint
    if report_year is not None:
        job.report_year = report_year
    if period_type is not None:
        job.period_type = period_type
    if quarter is not None or period_type == "annual":
        job.quarter = None if period_type == "annual" else quarter

    if statements is not None:
        draft = _loads(job.mapped_draft_json, {}) or {}
        # 只保留非 None
        clean: dict[str, dict[str, float]] = {}
        for kind, fields in statements.items():
            clean[kind] = {k: float(v) for k, v in fields.items() if v is not None}
        draft["statements"] = clean
        draft["report_year"] = job.report_year
        draft["period_type"] = job.period_type
        draft["quarter"] = job.quarter
        job.mapped_draft_json = _dumps(draft)
        if job.status == "failed" and clean:
            job.status = "review"
    db.commit()
    db.refresh(job)
    return job


def _filter_payload(fields: dict[str, float], allowed: set[str]) -> dict[str, float]:
    return {k: v for k, v in fields.items() if k in allowed and v is not None}


def commit_job(
    db: Session,
    job_id: int,
    *,
    company_id: int | None = None,
    overwrite: bool = True,
) -> ImportJob:
    job = get_job(db, job_id)
    if job.status == "committed":
        return job
    if job.status == "failed" and not _loads(job.mapped_draft_json, {}).get("statements"):
        raise ImportError(job.error_message or "任务失败，无法入库")

    draft = _loads(job.mapped_draft_json, {}) or {}
    statements = draft.get("statements") or {}
    year = job.report_year or draft.get("report_year")
    period_type = job.period_type or draft.get("period_type") or "annual"
    quarter = job.quarter if job.quarter is not None else draft.get("quarter")
    if period_type == "annual":
        quarter = None
    if year is None:
        raise ImportError("缺少报告年份，请先在预览中设置")

    # 企业
    cid = company_id or job.company_id
    if cid is None:
        name = job.company_hint or Path(job.original_filename).stem
        # 按名称查找
        existing = None
        for c in company_service.list_companies(db):
            if c.name == name or (job.company_code_hint and c.code == job.company_code_hint):
                existing = c
                break
        if existing:
            cid = existing.id
        else:
            created = company_service.create_company(
                db,
                CompanyCreate(
                    name=name,
                    code=job.company_code_hint,
                    industry=None,
                ),
            )
            cid = created.id
    else:
        company_service.get_company(db, cid)
    job.company_id = cid

    from app.core.constants import (
        BALANCE_SHEET_FIELDS,
        CASH_FLOW_FIELDS,
        INCOME_STATEMENT_FIELDS,
    )

    result_ids: dict[str, int] = {}
    kind_map = [
        (
            "balance",
            set(BALANCE_SHEET_FIELDS),
            statement_service.list_balance_sheets,
            statement_service.create_balance_sheet,
            statement_service.update_balance_sheet,
            BalanceSheetCreate,
            BalanceSheetUpdate,
        ),
        (
            "income",
            set(INCOME_STATEMENT_FIELDS),
            statement_service.list_income_statements,
            statement_service.create_income_statement,
            statement_service.update_income_statement,
            IncomeStatementCreate,
            IncomeStatementUpdate,
        ),
        (
            "cashflow",
            set(CASH_FLOW_FIELDS),
            statement_service.list_cash_flow_statements,
            statement_service.create_cash_flow_statement,
            statement_service.update_cash_flow_statement,
            CashFlowStatementCreate,
            CashFlowStatementUpdate,
        ),
    ]

    for kind, allowed, list_fn, create_fn, update_fn, CreateCls, UpdateCls in kind_map:
        fields = _filter_payload(statements.get(kind) or {}, allowed)
        if not fields and kind not in statements:
            continue
        payload_data = {
            "year": int(year),
            "period_type": period_type,
            "quarter": quarter,
            **fields,
        }
        # 查找已存在
        existing_rows = list_fn(db, cid, year=int(year), period_type=period_type)
        existed = None
        for r in existing_rows:
            if (r.quarter or None) == (quarter or None):
                existed = r
                break
        try:
            if existed is None:
                row = create_fn(db, cid, CreateCls(**payload_data))
                result_ids[kind] = row.id
            else:
                if not overwrite:
                    result_ids[kind] = existed.id
                    continue
                # update amounts only + period
                row = update_fn(db, cid, existed.id, UpdateCls(**payload_data))
                result_ids[kind] = row.id
        except ValidationError as exc:
            raise ImportError(exc.detail) from exc

    # L0 披露明细：与 L1 同事务
    disclosure_lines = draft.get("disclosure_lines") or []
    lines_written = 0
    if disclosure_lines:
        lines_written = disclosure_service.replace_import_lines(
            db,
            company_id=cid,
            year=int(year),
            period_type=period_type,
            quarter=quarter,
            import_job_id=job.id,
            lines=disclosure_lines,
            unit_scale=float(job.unit_scale or draft.get("unit_scale") or 1.0),
        )

    job.status = "committed"
    job.commit_result_json = _dumps(
        {
            "statement_ids": result_ids,
            "company_id": cid,
            "disclosure_lines_written": lines_written,
            "coa_version": draft.get("coa_version"),
        }
    )
    job.error_message = None
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job_id: int) -> None:
    job = get_job(db, job_id)
    # 删文件目录
    try:
        p = Path(job.file_path)
        if p.exists():
            shutil.rmtree(p.parent, ignore_errors=True)
    except Exception:
        pass
    db.delete(job)
    db.commit()


def job_to_dict(job: ImportJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "source_type": job.source_type,
        "original_filename": job.original_filename,
        "status": job.status,
        "company_hint": job.company_hint,
        "company_code_hint": job.company_code_hint,
        "company_id": job.company_id,
        "report_year": job.report_year,
        "period_type": job.period_type,
        "quarter": job.quarter,
        "accounting_standard": job.accounting_standard,
        "unit_scale": job.unit_scale,
        "scope": job.scope,
        "confidence": job.confidence,
        "fill_mode": job.fill_mode,
        "error_message": job.error_message,
        "coverage": _loads(job.coverage_json, {}),
        "issues": _loads(job.issues_json, []),
        "unmapped": _loads(job.unmapped_json, []),
        "disclosure_lines": (_loads(job.mapped_draft_json, {}) or {}).get(
            "disclosure_lines", []
        ),
        "draft": _loads(job.mapped_draft_json, {}),
        "raw_extract": _loads(job.raw_extract_json, {}),
        "commit_result": _loads(job.commit_result_json, None),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
