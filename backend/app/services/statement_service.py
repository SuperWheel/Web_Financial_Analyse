"""三大报表业务逻辑。

三表 CRUD 同构：通过 model 类 + 字段列表参数化，避免复制粘贴。
"""
from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import PERIOD_ANNUAL, PERIOD_QUARTERLY, QUARTERS
from app.models.balance_sheet import BalanceSheet
from app.models.base import Base
from app.models.cash_flow import CashFlowStatement
from app.models.income_statement import IncomeStatement
from app.services.company_service import get_company
from app.services.exceptions import ConflictError, NotFoundError, ServiceError

ModelT = TypeVar("ModelT", bound=Base)

# 报告期 + 主键字段，update 时单独处理
_PERIOD_KEYS = ("year", "period_type", "quarter")


class ValidationError(ServiceError):
    """业务层参数校验失败。"""

    status_code = 422


def _ensure_period_rules(year: int, period_type: str, quarter: int | None) -> None:
    if period_type == PERIOD_ANNUAL and quarter is not None:
        raise ValidationError("年报（annual）的 quarter 必须为空")
    if period_type == PERIOD_QUARTERLY:
        if quarter is None:
            raise ValidationError("季报（quarterly）必须指定 quarter（1-4）")
        if quarter not in QUARTERS:
            raise ValidationError(f"季度必须是 {list(QUARTERS)} 之一")


def _find_by_period(
    db: Session,
    model: type[ModelT],
    company_id: int,
    year: int,
    period_type: str,
    quarter: int | None,
    *,
    exclude_id: int | None = None,
) -> ModelT | None:
    """显式查找同报告期记录（处理 SQLite UNIQUE 对 NULL 不判等）。"""
    stmt = select(model).where(
        model.company_id == company_id,  # type: ignore[attr-defined]
        model.year == year,  # type: ignore[attr-defined]
        model.period_type == period_type,  # type: ignore[attr-defined]
    )
    if quarter is None:
        stmt = stmt.where(model.quarter.is_(None))  # type: ignore[attr-defined]
    else:
        stmt = stmt.where(model.quarter == quarter)  # type: ignore[attr-defined]
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)  # type: ignore[attr-defined]
    return db.scalars(stmt).first()


def list_statements(
    db: Session,
    model: type[ModelT],
    company_id: int,
    *,
    year: int | None = None,
    period_type: str | None = None,
) -> list[ModelT]:
    get_company(db, company_id)
    stmt = select(model).where(model.company_id == company_id)  # type: ignore[attr-defined]
    if year is not None:
        stmt = stmt.where(model.year == year)  # type: ignore[attr-defined]
    if period_type is not None:
        stmt = stmt.where(model.period_type == period_type)  # type: ignore[attr-defined]
    stmt = stmt.order_by(
        model.year.desc(),  # type: ignore[attr-defined]
        model.period_type.asc(),  # type: ignore[attr-defined]
        model.quarter.asc(),  # type: ignore[attr-defined]
    )
    return list(db.scalars(stmt).all())


def get_statement(
    db: Session, model: type[ModelT], company_id: int, statement_id: int
) -> ModelT:
    get_company(db, company_id)
    row = db.get(model, statement_id)
    if row is None or getattr(row, "company_id") != company_id:
        raise NotFoundError(f"报表 id={statement_id} 不存在")
    return row


def create_statement(
    db: Session,
    model: type[ModelT],
    company_id: int,
    payload: BaseModel,
) -> ModelT:
    get_company(db, company_id)
    data = payload.model_dump()
    year = data["year"]
    period_type = data["period_type"]
    quarter = data.get("quarter")
    _ensure_period_rules(year, period_type, quarter)

    if _find_by_period(db, model, company_id, year, period_type, quarter) is not None:
        raise ConflictError(
            f"该企业 {year} 年 {period_type}"
            + (f" Q{quarter}" if quarter else " 年报")
            + " 报表已存在"
        )

    row = model(company_id=company_id, **data)  # type: ignore[call-arg]
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("报告期冲突") from exc
    db.refresh(row)
    return row


def update_statement(
    db: Session,
    model: type[ModelT],
    company_id: int,
    statement_id: int,
    payload: BaseModel,
) -> ModelT:
    row = get_statement(db, model, company_id, statement_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return row

    year = data.get("year", getattr(row, "year"))
    period_type = data.get("period_type", getattr(row, "period_type"))
    # quarter 允许显式设为 null（年报切换）
    if "quarter" in data:
        quarter = data["quarter"]
    else:
        quarter = getattr(row, "quarter")

    # 若切换为年报且未显式传 quarter，强制清空
    if period_type == PERIOD_ANNUAL and "period_type" in data and "quarter" not in data:
        quarter = None
        data["quarter"] = None

    _ensure_period_rules(year, period_type, quarter)

    conflict = _find_by_period(
        db,
        model,
        company_id,
        year,
        period_type,
        quarter,
        exclude_id=statement_id,
    )
    if conflict is not None:
        raise ConflictError("目标报告期已存在其他报表")

    for field, value in data.items():
        setattr(row, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("报告期冲突") from exc
    db.refresh(row)
    return row


def delete_statement(
    db: Session, model: type[ModelT], company_id: int, statement_id: int
) -> None:
    row = get_statement(db, model, company_id, statement_id)
    db.delete(row)
    db.commit()


# ---- 三表薄封装（API 可读性）----

def list_balance_sheets(
    db: Session, company_id: int, *, year: int | None = None, period_type: str | None = None
) -> list[BalanceSheet]:
    return list_statements(db, BalanceSheet, company_id, year=year, period_type=period_type)


def get_balance_sheet(db: Session, company_id: int, statement_id: int) -> BalanceSheet:
    return get_statement(db, BalanceSheet, company_id, statement_id)


def create_balance_sheet(db: Session, company_id: int, payload: BaseModel) -> BalanceSheet:
    return create_statement(db, BalanceSheet, company_id, payload)


def update_balance_sheet(
    db: Session, company_id: int, statement_id: int, payload: BaseModel
) -> BalanceSheet:
    return update_statement(db, BalanceSheet, company_id, statement_id, payload)


def delete_balance_sheet(db: Session, company_id: int, statement_id: int) -> None:
    delete_statement(db, BalanceSheet, company_id, statement_id)


def list_income_statements(
    db: Session, company_id: int, *, year: int | None = None, period_type: str | None = None
) -> list[IncomeStatement]:
    return list_statements(
        db, IncomeStatement, company_id, year=year, period_type=period_type
    )


def get_income_statement(
    db: Session, company_id: int, statement_id: int
) -> IncomeStatement:
    return get_statement(db, IncomeStatement, company_id, statement_id)


def create_income_statement(
    db: Session, company_id: int, payload: BaseModel
) -> IncomeStatement:
    return create_statement(db, IncomeStatement, company_id, payload)


def update_income_statement(
    db: Session, company_id: int, statement_id: int, payload: BaseModel
) -> IncomeStatement:
    return update_statement(db, IncomeStatement, company_id, statement_id, payload)


def delete_income_statement(db: Session, company_id: int, statement_id: int) -> None:
    delete_statement(db, IncomeStatement, company_id, statement_id)


def list_cash_flow_statements(
    db: Session, company_id: int, *, year: int | None = None, period_type: str | None = None
) -> list[CashFlowStatement]:
    return list_statements(
        db, CashFlowStatement, company_id, year=year, period_type=period_type
    )


def get_cash_flow_statement(
    db: Session, company_id: int, statement_id: int
) -> CashFlowStatement:
    return get_statement(db, CashFlowStatement, company_id, statement_id)


def create_cash_flow_statement(
    db: Session, company_id: int, payload: BaseModel
) -> CashFlowStatement:
    return create_statement(db, CashFlowStatement, company_id, payload)


def update_cash_flow_statement(
    db: Session, company_id: int, statement_id: int, payload: BaseModel
) -> CashFlowStatement:
    return update_statement(db, CashFlowStatement, company_id, statement_id, payload)


def delete_cash_flow_statement(db: Session, company_id: int, statement_id: int) -> None:
    delete_statement(db, CashFlowStatement, company_id, statement_id)


# 避免未使用导入告警（Any 供类型扩展）
_ = Any
