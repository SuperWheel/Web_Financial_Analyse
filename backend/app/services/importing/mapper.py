"""科目映射：多级别名匹配 + 显式 rollup + 冲突消解。"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.rollup_rules import match_rollup
from app.core.subject_aliases import CORE_FIELDS, SUBJECT_ALIASES
from app.services.importing.extract import ExtractedTable, RawRow
from app.services.importing.text_utils import is_section_label, is_total_label, normalize_label


@dataclass
class MappedField:
    field: str
    amount: float
    confidence: float
    source_label: str
    source_page: int
    rule: str


@dataclass
class UnmappedRow:
    label: str
    amount: float | None
    page: int
    reason: str


@dataclass
class DisclosureLineDraft:
    """L0 披露行草稿（尚未落库）。"""

    statement: str
    line_no: int
    label_raw: str
    label_norm: str
    amount: float | None
    page_no: int | None
    role: str
    mapped_to: str | None
    map_rule: str
    map_confidence: float | None
    include_in_aggregate: bool


@dataclass
class MapResult:
    fields: dict[str, MappedField] = field(default_factory=dict)
    unmapped: list[UnmappedRow] = field(default_factory=list)
    disclosure_lines: list[DisclosureLineDraft] = field(default_factory=list)


def _alias_index(kind: str) -> list[tuple[str, str, int, list[str]]]:
    out: list[tuple[str, str, int, list[str]]] = []
    for field_name, entry in SUBJECT_ALIASES.get(kind, {}).items():
        tags = list(entry.get("tags") or [])
        pr = int(entry.get("priority") or 50)
        for al in entry.get("aliases") or []:
            out.append((field_name, normalize_label(al), pr, tags))
    out.sort(key=lambda x: -len(x[1]))
    return out


def _score(label_norm: str, alias_norm: str, row_is_total: bool, tags: list[str]) -> float:
    if not label_norm or not alias_norm:
        return 0.0
    score = 0.0
    if label_norm == alias_norm:
        score = 1.0
    elif label_norm.replace("其中:", "") == alias_norm or label_norm == "其中:" + alias_norm:
        score = 0.95
    elif alias_norm in label_norm and len(alias_norm) >= 4:
        score = (
            0.85
            if label_norm.startswith(alias_norm) or label_norm.endswith(alias_norm)
            else 0.78
        )
    elif label_norm in alias_norm and len(label_norm) >= 4:
        score = 0.8
    elif len(label_norm) >= 4 and len(alias_norm) >= 4:
        inter = sum(
            1 for i in range(len(alias_norm) - 1) if alias_norm[i : i + 2] in label_norm
        )
        if inter >= max(2, len(alias_norm) // 3):
            score = 0.62
    if score <= 0:
        return 0.0
    # 仅惩罚「合计行 → 非合计字段」
    if row_is_total and "total" not in tags:
        score -= 0.2
    return score


def _pick_amount(row: RawRow) -> float | None:
    if not row.amounts:
        return None
    amounts = list(row.amounts)
    filtered = [
        a
        for a in amounts
        if not (float(a).is_integer() and abs(a) < 100 and abs(a) != 0)
    ]
    if not filtered:
        filtered = amounts
    if row.source == "line" and len(filtered) >= 2:
        return filtered[-1]
    return filtered[0]


def _infer_role(label: str, label_norm: str, amount: float | None) -> str:
    if amount is None and (not label_norm or len(label_norm) < 2):
        return "header"
    if is_section_label(label, amount) and amount is None:
        return "header"
    if is_total_label(label) or "合计" in label_norm or "总计" in label_norm:
        if "小计" in label_norm:
            return "subtotal"
        return "total"
    if "小计" in label_norm:
        return "subtotal"
    return "detail"


def map_table(kind: str, table: ExtractedTable, unit_scale: float) -> MapResult:
    aliases = _alias_index(kind)
    result = MapResult()
    revenue_candidates: list[tuple[float, MappedField]] = []
    cost_candidates: list[tuple[float, MappedField]] = []
    profit_candidates: list[tuple[float, MappedField]] = []
    equity_candidates: list[tuple[float, MappedField]] = []
    parent_equity_candidates: list[tuple[float, MappedField]] = []
    parent_profit_candidates: list[tuple[float, MappedField]] = []

    line_no = 0
    for row in table.rows:
        label = row.label
        label_norm = normalize_label(label)
        amount = _pick_amount(row)
        if amount is not None:
            amount = amount * unit_scale

        role = _infer_role(label, label_norm, amount)
        if role == "header" or is_section_label(label, amount):
            if label_norm:
                result.disclosure_lines.append(
                    DisclosureLineDraft(
                        statement=kind,
                        line_no=line_no,
                        label_raw=label,
                        label_norm=label_norm,
                        amount=None,
                        page_no=row.page,
                        role="header",
                        mapped_to=None,
                        map_rule="none",
                        map_confidence=None,
                        include_in_aggregate=False,
                    )
                )
                line_no += 1
            continue
        if amount is None:
            continue

        line_no += 1
        # 营业总成本不作为营业成本（避免与营业成本混淆）
        if "营业总成本" in label_norm and "其中" not in label_norm:
            result.unmapped.append(
                UnmappedRow(label=label, amount=amount, page=row.page, reason="skip_total_cost")
            )
            result.disclosure_lines.append(
                DisclosureLineDraft(
                    statement=kind,
                    line_no=line_no,
                    label_raw=label,
                    label_norm=label_norm,
                    amount=amount,
                    page_no=row.page,
                    role=role,
                    mapped_to=None,
                    map_rule="none",
                    map_confidence=None,
                    include_in_aggregate=False,
                )
            )
            continue

        row_total = is_total_label(label)
        field_scores: dict[str, float] = {}
        for field_name, al, pr, tags in aliases:
            sc = _score(label_norm, al, row_total, tags)
            if sc <= 0:
                continue
            sc = sc + min(pr, 100) / 1000.0
            prev = field_scores.get(field_name)
            if prev is None or sc > prev:
                field_scores[field_name] = sc

        best_field: str | None = None
        best_sc = 0.0
        rule = "none"
        conf: float | None = None

        if field_scores:
            ranked = sorted(field_scores.items(), key=lambda x: -x[1])
            best_field, best_sc = ranked[0]
            second_sc = ranked[1][1] if len(ranked) > 1 else 0.0
            if best_sc < 0.75:
                best_field = None
                result.unmapped.append(
                    UnmappedRow(label=label, amount=amount, page=row.page, reason="low_score")
                )
            elif best_sc - second_sc < 0.05 and second_sc >= 0.75:
                best_field = None
                result.unmapped.append(
                    UnmappedRow(label=label, amount=amount, page=row.page, reason="ambiguous")
                )
            else:
                rule = "exact" if best_sc >= 0.98 else "alias"
                conf = min(0.99, best_sc)
        else:
            # 显式 rollup（仅 alias 全无命中时）
            rr = match_rollup(kind, label_norm)
            if rr is not None:
                best_field = rr["mapped_to"]
                rule = "rollup"
                conf = 0.8
                best_sc = 0.8
            else:
                result.unmapped.append(
                    UnmappedRow(
                        label=label, amount=amount, page=row.page, reason="no_alias_match"
                    )
                )

        include = bool(best_field) and role == "detail"
        # 合计类字段也写入 L1（校验/展示），不参与明细加总语义上由 total 优先
        if best_field and role == "total":
            include = True

        result.disclosure_lines.append(
            DisclosureLineDraft(
                statement=kind,
                line_no=line_no,
                label_raw=label,
                label_norm=label_norm,
                amount=amount,
                page_no=row.page,
                role=role,
                mapped_to=best_field,
                map_rule=rule if best_field else "none",
                map_confidence=conf,
                include_in_aggregate=include,
            )
        )

        if not best_field or conf is None:
            continue

        mf = MappedField(
            field=best_field,
            amount=amount,
            confidence=conf,
            source_label=label,
            source_page=row.page,
            rule=rule,
        )

        if best_field == "operating_revenue":
            bonus = 0.0
            if label_norm in {
                normalize_label("营业收入"),
                normalize_label("其中：营业收入"),
            }:
                bonus = 0.08
            if "营业总收入" in label_norm and "其中" not in label_norm:
                bonus -= 0.06
            revenue_candidates.append((conf + bonus, mf))
            continue

        if best_field == "operating_cost":
            bonus = (
                0.05
                if label_norm
                in {normalize_label("营业成本"), normalize_label("其中：营业成本")}
                else 0.0
            )
            cost_candidates.append((conf + bonus, mf))
            continue

        if best_field == "net_profit":
            bonus = 0.1 if label_norm == normalize_label("净利润") else 0.0
            if "归属于母公司" in label_norm or "归属母公司" in label_norm:
                bonus -= 0.02
            if "持续经营" in label_norm or "终止经营" in label_norm:
                bonus -= 0.05
            profit_candidates.append((conf + bonus, mf))
            continue

        if best_field == "net_profit_parent":
            parent_profit_candidates.append((conf, mf))
            continue

        if best_field == "total_equity":
            bonus = 0.0
            if "归属于" in label_norm or "少数股东" in label_norm:
                bonus -= 0.1
            if label_norm in {
                normalize_label("所有者权益合计"),
                normalize_label("所有者权益(或股东权益)合计"),
                normalize_label("所有者权益（或股东权益）合计"),
                normalize_label("股东权益合计"),
            }:
                bonus += 0.12
            equity_candidates.append((conf + bonus, mf))
            continue

        if best_field == "total_equity_parent":
            parent_equity_candidates.append((conf, mf))
            continue

        prev = result.fields.get(best_field)
        # rollup 可累加；高置信 alias 取更高置信
        if prev is None:
            result.fields[best_field] = mf
        elif rule == "rollup" and prev.rule == "rollup":
            result.fields[best_field] = MappedField(
                field=best_field,
                amount=prev.amount + amount,
                confidence=min(prev.confidence, conf),
                source_label=f"{prev.source_label}+{label}",
                source_page=row.page,
                rule="rollup",
            )
        elif conf > prev.confidence:
            result.fields[best_field] = mf

    if revenue_candidates:
        revenue_candidates.sort(key=lambda x: -x[0])
        result.fields["operating_revenue"] = revenue_candidates[0][1]
    if cost_candidates:
        cost_candidates.sort(key=lambda x: -x[0])
        result.fields["operating_cost"] = cost_candidates[0][1]
    if profit_candidates:
        profit_candidates.sort(key=lambda x: -x[0])
        result.fields["net_profit"] = profit_candidates[0][1]
    if parent_profit_candidates:
        parent_profit_candidates.sort(key=lambda x: -x[0])
        result.fields["net_profit_parent"] = parent_profit_candidates[0][1]
    if equity_candidates:
        equity_candidates.sort(key=lambda x: -x[0])
        result.fields["total_equity"] = equity_candidates[0][1]
    if parent_equity_candidates:
        parent_equity_candidates.sort(key=lambda x: -x[0])
        result.fields["total_equity_parent"] = parent_equity_candidates[0][1]

    return result


def coverage_stats(kind: str, mapped: dict[str, MappedField]) -> dict:
    core = CORE_FIELDS.get(kind, ())
    hit = sum(1 for f in core if f in mapped)
    return {
        "core_total": len(core),
        "core_hit": hit,
        "mapped_fields": len(mapped),
        "coverage": (hit / len(core)) if core else 0.0,
    }
