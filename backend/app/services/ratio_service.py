"""财务比率计算：只读 L1 三表，按公式动态计算，不落库。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import PERIOD_ANNUAL, RATIO_DEFINITIONS
from app.services.company_service import get_company
from app.services.statement_service import (
    list_balance_sheets,
    list_cash_flow_statements,
    list_income_statements,
)


@dataclass(frozen=True)
class PeriodKey:
    year: int
    period_type: str
    quarter: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "period_type": self.period_type,
            "quarter": self.quarter,
        }


def _money(row: Any, field: str) -> float | None:
    if row is None:
        return None
    val = getattr(row, field, None)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _div(
    num: float | None, den: float | None, *, missing: list[str]
) -> tuple[float | None, str | None]:
    if num is None or den is None:
        return None, "missing_fields"
    if den == 0:
        return None, "zero_denominator"
    return num / den, None


def _match_period(rows: list[Any], period: PeriodKey) -> Any | None:
    for r in rows:
        if (
            int(r.year) == period.year
            and r.period_type == period.period_type
            and (r.quarter or None) == (period.quarter or None)
        ):
            return r
    return None


def list_ratio_periods(db: Session, company_id: int) -> list[dict[str, Any]]:
    """有任意 L1 报表的期间（以资产负债表优先，并并入利润/现金流期间）。"""
    get_company(db, company_id)
    seen: dict[tuple[int, str, int | None], dict[str, Any]] = {}

    def add(row: Any, kind: str) -> None:
        q = row.quarter if row.quarter is not None else None
        key = (int(row.year), row.period_type, q)
        item = seen.get(key)
        if item is None:
            item = {
                "year": int(row.year),
                "period_type": row.period_type,
                "quarter": q,
                "has_balance": False,
                "has_income": False,
                "has_cashflow": False,
            }
            seen[key] = item
        item[f"has_{kind}"] = True

    for r in list_balance_sheets(db, company_id):
        add(r, "balance")
    for r in list_income_statements(db, company_id):
        add(r, "income")
    for r in list_cash_flow_statements(db, company_id):
        add(r, "cashflow")

    periods = list(seen.values())
    periods.sort(
        key=lambda p: (
            p["year"],
            0 if p["period_type"] == PERIOD_ANNUAL else 1,
            p["quarter"] or 0,
        ),
        reverse=True,
    )
    return periods


def compute_period_ratios(
    db: Session,
    company_id: int,
    *,
    year: int,
    period_type: str,
    quarter: int | None = None,
) -> dict[str, Any]:
    get_company(db, company_id)
    if period_type == PERIOD_ANNUAL:
        quarter = None

    period = PeriodKey(year=year, period_type=period_type, quarter=quarter)
    bs = _match_period(list_balance_sheets(db, company_id, year=year, period_type=period_type), period)
    inc = _match_period(
        list_income_statements(db, company_id, year=year, period_type=period_type), period
    )
    cf = _match_period(
        list_cash_flow_statements(db, company_id, year=year, period_type=period_type),
        period,
    )

    # 字段取值
    tca = _money(bs, "total_current_assets")
    tcl = _money(bs, "total_current_liabilities")
    inv = _money(bs, "inventories")
    cash = _money(bs, "monetary_funds")
    ta = _money(bs, "total_assets")
    tl = _money(bs, "total_liabilities")
    te = _money(bs, "total_equity")
    te_p = _money(bs, "total_equity_parent")
    rev = _money(inc, "operating_revenue")
    cost = _money(inc, "operating_cost")
    op = _money(inc, "operating_profit")
    np_ = _money(inc, "net_profit")
    np_p = _money(inc, "net_profit_parent")
    cfo = _money(cf, "net_cash_flow_operating")

    results: list[dict[str, Any]] = []

    def push(
        key: str,
        value: float | None,
        *,
        formula: str,
        missing: list[str] | None = None,
        reason: str | None = None,
        extras: dict[str, Any] | None = None,
    ) -> None:
        meta = next(m for m in RATIO_DEFINITIONS if m["key"] == key)
        item: dict[str, Any] = {
            "key": key,
            "name": meta["name"],
            "group": meta["group"],
            "unit": meta["unit"],
            "description": meta["description"],
            "formula": formula,
            "value": None if value is None else round(float(value), 6),
            "missing": missing or [],
            "reason": reason,
        }
        if extras:
            item.update(extras)
        results.append(item)

    # 偿债
    miss: list[str] = []
    if tca is None:
        miss.append("total_current_assets")
    if tcl is None:
        miss.append("total_current_liabilities")
    v, why = _div(tca, tcl, missing=miss)
    push("current_ratio", v, formula="total_current_assets / total_current_liabilities", missing=miss, reason=why)

    miss = []
    quick_num = None
    if tca is None:
        miss.append("total_current_assets")
    else:
        quick_num = tca - (inv or 0.0)
    if tcl is None:
        miss.append("total_current_liabilities")
    v, why = _div(quick_num, tcl, missing=miss)
    push(
        "quick_ratio",
        v,
        formula="(total_current_assets - inventories) / total_current_liabilities",
        missing=miss,
        reason=why,
    )

    miss = []
    if cash is None:
        miss.append("monetary_funds")
    if tcl is None:
        miss.append("total_current_liabilities")
    v, why = _div(cash, tcl, missing=miss)
    push("cash_ratio", v, formula="monetary_funds / total_current_liabilities", missing=miss, reason=why)

    miss = []
    if tl is None:
        miss.append("total_liabilities")
    if ta is None:
        miss.append("total_assets")
    v, why = _div(tl, ta, missing=miss)
    push("debt_to_asset", v, formula="total_liabilities / total_assets", missing=miss, reason=why)

    miss = []
    if te is None:
        miss.append("total_equity")
    if ta is None:
        miss.append("total_assets")
    v, why = _div(te, ta, missing=miss)
    push("equity_ratio", v, formula="total_equity / total_assets", missing=miss, reason=why)

    miss = []
    if tl is None:
        miss.append("total_liabilities")
    if te is None:
        miss.append("total_equity")
    v, why = _div(tl, te, missing=miss)
    push("debt_to_equity", v, formula="total_liabilities / total_equity", missing=miss, reason=why)

    # 盈利
    miss = []
    gross = None
    if rev is None:
        miss.append("operating_revenue")
    if cost is None:
        miss.append("operating_cost")
    if rev is not None and cost is not None:
        gross = rev - cost
    v, why = _div(gross, rev, missing=miss)
    push(
        "gross_margin",
        v,
        formula="(operating_revenue - operating_cost) / operating_revenue",
        missing=miss,
        reason=why,
    )

    miss = []
    if op is None:
        miss.append("operating_profit")
    if rev is None:
        miss.append("operating_revenue")
    v, why = _div(op, rev, missing=miss)
    push("operating_margin", v, formula="operating_profit / operating_revenue", missing=miss, reason=why)

    miss = []
    if np_ is None:
        miss.append("net_profit")
    if rev is None:
        miss.append("operating_revenue")
    v, why = _div(np_, rev, missing=miss)
    push("net_margin", v, formula="net_profit / operating_revenue", missing=miss, reason=why)

    # ROE 口径
    roe_num, roe_den, roe_variant = None, None, "net_profit / total_equity"
    miss = []
    if np_p is not None and te_p is not None and te_p != 0:
        roe_num, roe_den = np_p, te_p
        roe_variant = "net_profit_parent / total_equity_parent"
    else:
        if np_ is None:
            miss.append("net_profit")
        if te is None:
            miss.append("total_equity")
        roe_num, roe_den = np_, te
    v, why = _div(roe_num, roe_den, missing=miss)
    push(
        "roe",
        v,
        formula=roe_variant,
        missing=miss,
        reason=why,
        extras={"variant": roe_variant},
    )

    miss = []
    if np_ is None:
        miss.append("net_profit")
    if ta is None:
        miss.append("total_assets")
    v, why = _div(np_, ta, missing=miss)
    push("roa", v, formula="net_profit / total_assets", missing=miss, reason=why)

    miss = []
    if rev is None:
        miss.append("operating_revenue")
    if ta is None:
        miss.append("total_assets")
    v, why = _div(rev, ta, missing=miss)
    push("asset_turnover", v, formula="operating_revenue / total_assets", missing=miss, reason=why)

    miss = []
    if cfo is None:
        miss.append("net_cash_flow_operating")
    if rev is None:
        miss.append("operating_revenue")
    v, why = _div(cfo, rev, missing=miss)
    push(
        "ocfr",
        v,
        formula="net_cash_flow_operating / operating_revenue",
        missing=miss,
        reason=why,
    )

    available = sum(1 for r in results if r["value"] is not None)
    return {
        "company_id": company_id,
        "period": period.as_dict(),
        "sources": {
            "balance_sheet_id": getattr(bs, "id", None),
            "income_statement_id": getattr(inc, "id", None),
            "cash_flow_statement_id": getattr(cf, "id", None),
        },
        "ratios": results,
        "summary": {
            "total": len(results),
            "available": available,
            "unavailable": len(results) - available,
        },
    }


def compute_ratio_history(
    db: Session,
    company_id: int,
    *,
    period_type: str = PERIOD_ANNUAL,
    keys: list[str] | None = None,
) -> dict[str, Any]:
    """多期比率序列，供折线图。"""
    periods = [
        p
        for p in list_ratio_periods(db, company_id)
        if p["period_type"] == period_type
    ]
    wanted = set(keys) if keys else {m["key"] for m in RATIO_DEFINITIONS}
    series: dict[str, list[dict[str, Any]]] = {k: [] for k in wanted}

    period_points: list[dict[str, Any]] = []
    for p in periods:
        snap = compute_period_ratios(
            db,
            company_id,
            year=p["year"],
            period_type=p["period_type"],
            quarter=p["quarter"],
        )
        period_points.append(snap["period"])
        by_key = {r["key"]: r for r in snap["ratios"]}
        for k in wanted:
            item = by_key.get(k)
            series[k].append(
                {
                    **snap["period"],
                    "value": item["value"] if item else None,
                    "reason": item.get("reason") if item else "unknown",
                }
            )

    meta = {m["key"]: m for m in RATIO_DEFINITIONS}
    return {
        "company_id": company_id,
        "period_type": period_type,
        "periods": period_points,
        "series": {
            k: {
                "key": k,
                "name": meta.get(k, {}).get("name", k),
                "group": meta.get(k, {}).get("group"),
                "unit": meta.get(k, {}).get("unit"),
                "points": pts,
            }
            for k, pts in series.items()
        },
    }
