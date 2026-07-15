"""导入草稿校验与填入模式决策。"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.subject_aliases import CORE_FIELDS
from app.services.importing.mapper import MappedField


@dataclass
class ValidationResult:
    hard_pass: bool
    fill_mode: str
    confidence: float
    issues: list[str] = field(default_factory=list)
    core_hit: int = 0
    core_total: int = 0


def _get(fields: dict[str, MappedField], key: str) -> float | None:
    m = fields.get(key)
    return m.amount if m else None


def validate_draft(
    *,
    extractability: float,
    locate_score: float,
    unit_scale: float,
    unit_confidence: float,
    year: int | None,
    statements: dict[str, dict[str, MappedField]],
) -> ValidationResult:
    issues: list[str] = []
    core_hit = 0
    core_total = 0
    confidences: list[float] = []

    mapped_count = 0
    for kind, fields in statements.items():
        mapped_count += len(fields)
        for mf in fields.values():
            confidences.append(mf.confidence)
        for f in CORE_FIELDS.get(kind, ()):
            core_total += 1
            if f in fields:
                core_hit += 1

    hard_ok = True
    if extractability < 0.25:
        hard_ok = False
        issues.append("文档可抽取性过低")
    if mapped_count < 5:
        hard_ok = False
        issues.append("映射字段过少")
    if core_hit < 6:
        hard_ok = False
        issues.append(f"核心字段命中不足（{core_hit}/{core_total}）")
    if year is None or not (1990 <= year <= 2100):
        hard_ok = False
        issues.append("未能识别报告年份")
    if unit_confidence < 0.4:
        issues.append("金额单位不确定，请人工确认")

    # 软勾稽
    bs = statements.get("balance") or {}
    ta = _get(bs, "total_assets")
    tl = _get(bs, "total_liabilities")
    te = _get(bs, "total_equity")
    if ta is not None and tl is not None and te is not None:
        gap = abs(ta - (tl + te))
        tol = max(1.0, 0.005 * abs(ta))
        if gap > tol:
            issues.append(
                f"资产负债勾稽不平衡：资产{ta:.2f} vs 负债+权益{tl + te:.2f}（差{gap:.2f}）"
            )

    coverage = (core_hit / core_total) if core_total else 0.0
    mean_c = sum(confidences) / len(confidences) if confidences else 0.0
    C = (
        0.25 * extractability
        + 0.25 * locate_score
        + 0.30 * mean_c
        + 0.20 * coverage
    )
    if any("不平衡" in x for x in issues):
        C -= 0.08
    C = max(0.0, min(1.0, C))

    soft_bs_ok = not any("不平衡" in x for x in issues)
    if hard_ok and C >= 0.80 and soft_bs_ok:
        mode = "AUTO_COMMIT_CANDIDATE"
    elif hard_ok and C >= 0.55:
        mode = "REVIEW_REQUIRED"
    else:
        mode = "REJECT_OR_MANUAL"
        if hard_ok:
            issues.append("置信度不足，请人工核对后入库")

    return ValidationResult(
        hard_pass=hard_ok,
        fill_mode=mode,
        confidence=round(C, 4),
        issues=issues,
        core_hit=core_hit,
        core_total=core_total,
    )
