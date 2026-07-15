"""科目级多期对比：只读 L1 三表，环比与结构动态计算，不落库。"""
from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.constants import (
    BALANCE_SHEET_GROUPS,
    CASH_FLOW_GROUPS,
    INCOME_STATEMENT_GROUPS,
    PERIOD_ANNUAL,
    PERIOD_QUARTERLY,
)
from app.models.balance_sheet import BalanceSheet
from app.models.cash_flow import CashFlowStatement
from app.models.income_statement import IncomeStatement
from app.services.company_service import get_company
from app.services.exceptions import ServiceError
from app.services.ratio_service import list_ratio_periods
from app.services.statement_service import (
    list_balance_sheets,
    list_cash_flow_statements,
    list_income_statements,
)

StatementType = Literal["balance", "income", "cashflow"]

_STATEMENT_CONFIG: dict[str, dict[str, Any]] = {
    "balance": {
        "groups": BALANCE_SHEET_GROUPS,
        "list_fn": list_balance_sheets,
        "model": BalanceSheet,
        "base_field": "total_assets",
        "base_label": "资产总计",
    },
    "income": {
        "groups": INCOME_STATEMENT_GROUPS,
        "list_fn": list_income_statements,
        "model": IncomeStatement,
        "base_field": "operating_revenue",
        "base_label": "营业收入",
    },
    "cashflow": {
        "groups": CASH_FLOW_GROUPS,
        "list_fn": list_cash_flow_statements,
        "model": CashFlowStatement,
        "base_field": None,
        "base_label": None,
    },
}


class ValidationError(ServiceError):
    """业务层参数校验失败。"""

    status_code = 422


def list_compare_periods(db: Session, company_id: int) -> list[dict[str, Any]]:
    """有任意 L1 报表的期间（与比率期间同源）。"""
    return list_ratio_periods(db, company_id)


def _period_label(year: int, period_type: str, quarter: int | None) -> str:
    if period_type == PERIOD_ANNUAL:
        return f"{year} 年报"
    return f"{year} Q{quarter}"


def _money(row: Any | None, field: str) -> float | None:
    if row is None:
        return None
    val = getattr(row, field, None)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _delta(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None:
        return None
    return curr - prev


def _delta_pct(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None:
        return None
    if prev == 0:
        return None
    return (curr - prev) / abs(prev)


def _structure(value: float | None, base: float | None) -> float | None:
    if value is None or base is None or base == 0:
        return None
    return value / base


def build_compare_matrix(
    db: Session,
    company_id: int,
    *,
    statement_type: str,
    period_type: str = PERIOD_ANNUAL,
    years: list[int] | None = None,
) -> dict[str, Any]:
    """构建科目 × 期间矩阵（时间升序）。"""
    get_company(db, company_id)

    if statement_type not in _STATEMENT_CONFIG:
        raise ValidationError("statement_type 须为 balance、income 或 cashflow")
    if period_type not in (PERIOD_ANNUAL, PERIOD_QUARTERLY):
        raise ValidationError("period_type 须为 annual 或 quarterly")

    cfg = _STATEMENT_CONFIG[statement_type]
    list_fn = cfg["list_fn"]
    rows: list[Any] = list_fn(db, company_id)

    # 过滤 period_type / years
    year_set = set(years) if years else None
    filtered: list[Any] = []
    for r in rows:
        if r.period_type != period_type:
            continue
        if year_set is not None and int(r.year) not in year_set:
            continue
        filtered.append(r)

    # 期间轴：升序
    filtered.sort(
        key=lambda r: (
            int(r.year),
            r.quarter if r.quarter is not None else 0,
        )
    )

    periods_meta: list[dict[str, Any]] = []
    for r in filtered:
        q = r.quarter if r.quarter is not None else None
        periods_meta.append(
            {
                "year": int(r.year),
                "period_type": r.period_type,
                "quarter": q,
                "label": _period_label(int(r.year), r.period_type, q),
                "statement_id": int(r.id),
            }
        )

    n = len(filtered)
    base_field: str | None = cfg["base_field"]
    bases: list[float | None] = (
        [_money(r, base_field) for r in filtered] if base_field else [None] * n
    )

    groups_out: list[dict[str, Any]] = []
    for g in cfg["groups"]:
        field_rows: list[dict[str, Any]] = []
        for f in g["fields"]:
            key = f["key"]
            values = [_money(r, key) for r in filtered]
            deltas: list[float | None] = []
            delta_pcts: list[float | None] = []
            structure_pcts: list[float | None] = []
            for i in range(n):
                prev = values[i - 1] if i > 0 else None
                deltas.append(_delta(values[i], prev) if i > 0 else None)
                delta_pcts.append(_delta_pct(values[i], prev) if i > 0 else None)
                structure_pcts.append(
                    _structure(values[i], bases[i]) if base_field else None
                )
            field_rows.append(
                {
                    "key": key,
                    "label": f["label"],
                    "values": values,
                    "deltas": deltas,
                    "delta_pcts": delta_pcts,
                    "structure_pcts": structure_pcts,
                }
            )
        groups_out.append(
            {
                "key": g["key"],
                "label": g["label"],
                "rows": field_rows,
            }
        )

    return {
        "company_id": company_id,
        "statement_type": statement_type,
        "period_type": period_type,
        "base_field": base_field,
        "base_label": cfg["base_label"],
        "periods": periods_meta,
        "groups": groups_out,
    }
