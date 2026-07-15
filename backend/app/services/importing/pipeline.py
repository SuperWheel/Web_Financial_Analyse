"""导入管道编排：profile → locate → extract → map → validate。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.constants import COA_VERSION
from app.services.importing.extract import extract_segment
from app.services.importing.locate import locate_statements
from app.services.importing.mapper import MapResult, MappedField, coverage_stats, map_table
from app.services.importing.profile import build_profile
from app.services.importing.validate import ValidationResult, validate_draft


@dataclass
class PipelineResult:
    ok: bool
    status: str  # mapped / failed
    profile: dict[str, Any]
    segments: list[dict[str, Any]] = field(default_factory=list)
    statements: dict[str, dict[str, float]] = field(default_factory=dict)
    mapped_detail: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    unmapped: list[dict[str, Any]] = field(default_factory=list)
    disclosure_lines: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    confidence: float = 0.0
    fill_mode: str = "REJECT_OR_MANUAL"
    company_hint: str | None = None
    company_code_hint: str | None = None
    report_year: int | None = None
    period_type: str = "annual"
    quarter: int | None = None
    unit_scale: float = 1.0
    accounting_standard: str = "unknown"
    scope: str = "consolidated"
    coa_version: str = COA_VERSION
    error_message: str | None = None
    raw_extract: dict[str, Any] = field(default_factory=dict)

    def to_draft_dict(self) -> dict[str, Any]:
        return {
            "statements": self.statements,
            "mapped_detail": self.mapped_detail,
            "disclosure_lines": self.disclosure_lines,
            "company_hint": self.company_hint,
            "company_code_hint": self.company_code_hint,
            "report_year": self.report_year,
            "period_type": self.period_type,
            "quarter": self.quarter,
            "unit_scale": self.unit_scale,
            "accounting_standard": self.accounting_standard,
            "scope": self.scope,
            "coa_version": self.coa_version,
            "confidence": self.confidence,
            "fill_mode": self.fill_mode,
            "issues": self.issues,
            "coverage": self.coverage,
        }


def _mf_dict(mf: MappedField) -> dict[str, Any]:
    return {
        "field": mf.field,
        "amount": mf.amount,
        "confidence": mf.confidence,
        "source_label": mf.source_label,
        "source_page": mf.source_page,
        "rule": mf.rule,
    }


def _line_dict(line: Any) -> dict[str, Any]:
    return {
        "statement": line.statement,
        "line_no": line.line_no,
        "label_raw": line.label_raw,
        "label_norm": line.label_norm,
        "amount": line.amount,
        "page_no": line.page_no,
        "role": line.role,
        "mapped_to": line.mapped_to,
        "map_rule": line.map_rule,
        "map_confidence": line.map_confidence,
        "include_in_aggregate": line.include_in_aggregate,
    }


def run_pipeline_on_path(pdf_path: str | Path) -> PipelineResult:
    path = Path(pdf_path)
    profile = build_profile(path)
    base_profile = {
        "page_count": profile.page_count,
        "extractability": profile.extractability,
        "cjk_ratio": profile.cjk_ratio,
        "standard": profile.standard,
        "unit_scale": profile.unit_scale,
        "unit_confidence": profile.unit_confidence,
        "diagnostics": profile.diagnostics,
        "years": profile.years,
    }

    if profile.extractability < 0.25:
        return PipelineResult(
            ok=False,
            status="failed",
            profile=base_profile,
            error_message="PDF 文本不可靠（CID/扫描/乱码），请改用巨潮 Excel 或清晰数字版 PDF",
            company_hint=profile.company_hint,
            company_code_hint=profile.company_code_hint,
            unit_scale=profile.unit_scale,
            accounting_standard=profile.standard,
            fill_mode="REJECT_OR_MANUAL",
            issues=list(profile.diagnostics),
        )

    segments = locate_statements(str(path))
    if not segments:
        return PipelineResult(
            ok=False,
            status="failed",
            profile=base_profile,
            error_message="未能定位三大报表标题（合并资产负债表/利润表/现金流量表）",
            company_hint=profile.company_hint,
            company_code_hint=profile.company_code_hint,
            unit_scale=profile.unit_scale,
            accounting_standard=profile.standard,
            fill_mode="REJECT_OR_MANUAL",
        )

    seg_info = [
        {
            "kind": s.kind,
            "scope": s.scope,
            "start_page": s.start_page + 1,
            "end_page": s.end_page + 1,
            "title": s.title,
            "score": s.score,
        }
        for s in segments
    ]
    locate_score = min(1.0, sum(s.score for s in segments) / 3.0)

    mapped_by_kind: dict[str, dict[str, MappedField]] = {}
    unmapped_all: list[dict[str, Any]] = []
    disclosure_all: list[dict[str, Any]] = []
    raw_extract: dict[str, Any] = {}
    coverage: dict[str, Any] = {}

    for seg in segments:
        table = extract_segment(str(path), seg)
        raw_extract[seg.kind] = {
            "channel": table.channel,
            "row_count": len(table.rows),
            "header_years": table.header_years,
            "sample": [
                {"label": r.label, "amounts": r.amounts[:4], "page": r.page}
                for r in table.rows[:8]
            ],
        }
        mr: MapResult = map_table(seg.kind, table, profile.unit_scale)
        mapped_by_kind[seg.kind] = mr.fields
        coverage[seg.kind] = coverage_stats(seg.kind, mr.fields)
        for u in mr.unmapped:
            unmapped_all.append(
                {
                    "statement": seg.kind,
                    "label": u.label,
                    "amount": u.amount,
                    "page": u.page,
                    "reason": u.reason,
                }
            )
        for line in mr.disclosure_lines:
            disclosure_all.append(_line_dict(line))

    # 年份：优先表头年份，避免审计落款干扰
    header_years: list[int] = []
    for kind_raw in raw_extract.values():
        header_years.extend(kind_raw.get("header_years") or [])
    header_years = sorted({y for y in header_years if 1990 <= y <= 2100}, reverse=True)
    profile_years = sorted({y for y in profile.years if 1990 <= y <= 2100}, reverse=True)
    year = header_years[0] if header_years else (profile_years[0] if profile_years else None)

    statements_simple = {
        kind: {f: mf.amount for f, mf in fields.items()}
        for kind, fields in mapped_by_kind.items()
    }
    mapped_detail = {
        kind: [_mf_dict(mf) for mf in fields.values()]
        for kind, fields in mapped_by_kind.items()
    }

    vr: ValidationResult = validate_draft(
        extractability=profile.extractability,
        locate_score=locate_score,
        unit_scale=profile.unit_scale,
        unit_confidence=profile.unit_confidence,
        year=year,
        statements=mapped_by_kind,
    )

    scope = "consolidated"
    if segments and all(s.scope == "parent" for s in segments):
        scope = "parent"

    has_mapped = any(bool(v) for v in mapped_by_kind.values())
    status = "mapped" if has_mapped else "failed"
    err = None if has_mapped else "未能映射到有效报表科目"
    ok = has_mapped

    return PipelineResult(
        ok=ok,
        status=status,
        profile=base_profile,
        segments=seg_info,
        statements=statements_simple,
        mapped_detail=mapped_detail,
        unmapped=unmapped_all[:200],
        disclosure_lines=disclosure_all[:2000],
        coverage=coverage,
        issues=vr.issues + list(profile.diagnostics),
        confidence=vr.confidence,
        fill_mode=vr.fill_mode if status == "mapped" else "REJECT_OR_MANUAL",
        company_hint=profile.company_hint,
        company_code_hint=profile.company_code_hint,
        report_year=year,
        period_type="annual",
        quarter=None,
        unit_scale=profile.unit_scale,
        accounting_standard=profile.standard,
        scope=scope,
        coa_version=COA_VERSION,
        error_message=err,
        raw_extract=raw_extract,
    )


def parse_filing_pdf(pdf_path: str | Path) -> PipelineResult:
    return run_pipeline_on_path(pdf_path)
