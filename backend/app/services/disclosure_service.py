"""披露明细（L0）读写。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.disclosure_line import StatementDisclosureLine


def replace_import_lines(
    db: Session,
    *,
    company_id: int,
    year: int,
    period_type: str,
    quarter: int | None,
    import_job_id: int | None,
    lines: list[dict[str, Any]],
    unit_scale: float = 1.0,
) -> int:
    """替换某报告期下 source=import 的全部披露行，写入新行。返回写入条数。"""
    stmt = delete(StatementDisclosureLine).where(
        StatementDisclosureLine.company_id == company_id,
        StatementDisclosureLine.year == year,
        StatementDisclosureLine.period_type == period_type,
        StatementDisclosureLine.source == "import",
    )
    if quarter is None:
        stmt = stmt.where(StatementDisclosureLine.quarter.is_(None))
    else:
        stmt = stmt.where(StatementDisclosureLine.quarter == quarter)
    db.execute(stmt)

    count = 0
    for raw in lines:
        kind = raw.get("statement") or raw.get("statement_kind")
        label = raw.get("label_raw") or raw.get("label") or ""
        if not kind or not label:
            continue
        row = StatementDisclosureLine(
            company_id=company_id,
            statement_kind=str(kind),
            year=year,
            period_type=period_type,
            quarter=quarter,
            source="import",
            import_job_id=import_job_id,
            line_no=raw.get("line_no"),
            label_raw=str(label)[:512],
            label_norm=(raw.get("label_norm") or None),
            amount=raw.get("amount"),
            unit_scale_applied=float(raw.get("unit_scale_applied") or unit_scale or 1.0),
            role=raw.get("role"),
            page_no=raw.get("page_no") if raw.get("page_no") is not None else raw.get("page"),
            section_hint=raw.get("section_hint"),
            mapped_to=raw.get("mapped_to"),
            map_rule=raw.get("map_rule") or "none",
            map_confidence=raw.get("map_confidence"),
            include_in_aggregate=bool(raw.get("include_in_aggregate", True)),
        )
        db.add(row)
        count += 1
    return count


def list_lines(
    db: Session,
    company_id: int,
    *,
    year: int | None = None,
    period_type: str | None = None,
    statement_kind: str | None = None,
    only_unmapped: bool = False,
    limit: int = 2000,
) -> list[StatementDisclosureLine]:
    stmt = select(StatementDisclosureLine).where(
        StatementDisclosureLine.company_id == company_id
    )
    if year is not None:
        stmt = stmt.where(StatementDisclosureLine.year == year)
    if period_type is not None:
        stmt = stmt.where(StatementDisclosureLine.period_type == period_type)
    if statement_kind is not None:
        stmt = stmt.where(StatementDisclosureLine.statement_kind == statement_kind)
    if only_unmapped:
        stmt = stmt.where(StatementDisclosureLine.mapped_to.is_(None))
    stmt = stmt.order_by(
        StatementDisclosureLine.statement_kind,
        StatementDisclosureLine.line_no.nulls_last(),
        StatementDisclosureLine.id,
    ).limit(limit)
    return list(db.scalars(stmt).all())
