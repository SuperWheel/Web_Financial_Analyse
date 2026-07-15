"""三大报表路由 —— 嵌套于企业资源下。

只做请求/响应转换与依赖注入，业务在 statement_service。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.statement import (
    BalanceSheetCreate,
    BalanceSheetRead,
    BalanceSheetUpdate,
    CashFlowStatementCreate,
    CashFlowStatementRead,
    CashFlowStatementUpdate,
    IncomeStatementCreate,
    IncomeStatementRead,
    IncomeStatementUpdate,
)
from app.services import statement_service
from app.services.exceptions import ConflictError, NotFoundError, ServiceError
from app.services.statement_service import ValidationError

router = APIRouter(prefix="/companies/{company_id}", tags=["三大报表"])


def _to_http(exc: ServiceError):
    from fastapi import HTTPException

    return HTTPException(status_code=exc.status_code, detail=exc.detail)


# ---------------------------------------------------------------------------
# 资产负债表
# ---------------------------------------------------------------------------


@router.get("/balance-sheets", response_model=list[BalanceSheetRead])
def list_balance_sheets(
    company_id: int,
    year: int | None = Query(default=None),
    period_type: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[BalanceSheetRead]:
    try:
        rows = statement_service.list_balance_sheets(
            db, company_id, year=year, period_type=period_type
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    return [BalanceSheetRead.model_validate(r) for r in rows]


@router.post(
    "/balance-sheets",
    response_model=BalanceSheetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_balance_sheet(
    company_id: int,
    payload: BalanceSheetCreate,
    db: Session = Depends(get_session),
) -> BalanceSheetRead:
    try:
        row = statement_service.create_balance_sheet(db, company_id, payload)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _to_http(exc)
    return BalanceSheetRead.model_validate(row)


@router.get("/balance-sheets/{statement_id}", response_model=BalanceSheetRead)
def get_balance_sheet(
    company_id: int, statement_id: int, db: Session = Depends(get_session)
) -> BalanceSheetRead:
    try:
        row = statement_service.get_balance_sheet(db, company_id, statement_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return BalanceSheetRead.model_validate(row)


@router.patch("/balance-sheets/{statement_id}", response_model=BalanceSheetRead)
def update_balance_sheet(
    company_id: int,
    statement_id: int,
    payload: BalanceSheetUpdate,
    db: Session = Depends(get_session),
) -> BalanceSheetRead:
    try:
        row = statement_service.update_balance_sheet(
            db, company_id, statement_id, payload
        )
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _to_http(exc)
    return BalanceSheetRead.model_validate(row)


@router.delete(
    "/balance-sheets/{statement_id}",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_balance_sheet(
    company_id: int, statement_id: int, db: Session = Depends(get_session)
) -> Response:
    try:
        statement_service.delete_balance_sheet(db, company_id, statement_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 利润表
# ---------------------------------------------------------------------------


@router.get("/income-statements", response_model=list[IncomeStatementRead])
def list_income_statements(
    company_id: int,
    year: int | None = Query(default=None),
    period_type: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[IncomeStatementRead]:
    try:
        rows = statement_service.list_income_statements(
            db, company_id, year=year, period_type=period_type
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    return [IncomeStatementRead.model_validate(r) for r in rows]


@router.post(
    "/income-statements",
    response_model=IncomeStatementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_income_statement(
    company_id: int,
    payload: IncomeStatementCreate,
    db: Session = Depends(get_session),
) -> IncomeStatementRead:
    try:
        row = statement_service.create_income_statement(db, company_id, payload)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _to_http(exc)
    return IncomeStatementRead.model_validate(row)


@router.get("/income-statements/{statement_id}", response_model=IncomeStatementRead)
def get_income_statement(
    company_id: int, statement_id: int, db: Session = Depends(get_session)
) -> IncomeStatementRead:
    try:
        row = statement_service.get_income_statement(db, company_id, statement_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return IncomeStatementRead.model_validate(row)


@router.patch("/income-statements/{statement_id}", response_model=IncomeStatementRead)
def update_income_statement(
    company_id: int,
    statement_id: int,
    payload: IncomeStatementUpdate,
    db: Session = Depends(get_session),
) -> IncomeStatementRead:
    try:
        row = statement_service.update_income_statement(
            db, company_id, statement_id, payload
        )
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _to_http(exc)
    return IncomeStatementRead.model_validate(row)


@router.delete(
    "/income-statements/{statement_id}",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_income_statement(
    company_id: int, statement_id: int, db: Session = Depends(get_session)
) -> Response:
    try:
        statement_service.delete_income_statement(db, company_id, statement_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 现金流量表
# ---------------------------------------------------------------------------


@router.get("/cash-flow-statements", response_model=list[CashFlowStatementRead])
def list_cash_flow_statements(
    company_id: int,
    year: int | None = Query(default=None),
    period_type: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> list[CashFlowStatementRead]:
    try:
        rows = statement_service.list_cash_flow_statements(
            db, company_id, year=year, period_type=period_type
        )
    except NotFoundError as exc:
        raise _to_http(exc)
    return [CashFlowStatementRead.model_validate(r) for r in rows]


@router.post(
    "/cash-flow-statements",
    response_model=CashFlowStatementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_cash_flow_statement(
    company_id: int,
    payload: CashFlowStatementCreate,
    db: Session = Depends(get_session),
) -> CashFlowStatementRead:
    try:
        row = statement_service.create_cash_flow_statement(db, company_id, payload)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _to_http(exc)
    return CashFlowStatementRead.model_validate(row)


@router.get(
    "/cash-flow-statements/{statement_id}", response_model=CashFlowStatementRead
)
def get_cash_flow_statement(
    company_id: int, statement_id: int, db: Session = Depends(get_session)
) -> CashFlowStatementRead:
    try:
        row = statement_service.get_cash_flow_statement(db, company_id, statement_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return CashFlowStatementRead.model_validate(row)


@router.patch(
    "/cash-flow-statements/{statement_id}", response_model=CashFlowStatementRead
)
def update_cash_flow_statement(
    company_id: int,
    statement_id: int,
    payload: CashFlowStatementUpdate,
    db: Session = Depends(get_session),
) -> CashFlowStatementRead:
    try:
        row = statement_service.update_cash_flow_statement(
            db, company_id, statement_id, payload
        )
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _to_http(exc)
    return CashFlowStatementRead.model_validate(row)


@router.delete(
    "/cash-flow-statements/{statement_id}",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_cash_flow_statement(
    company_id: int, statement_id: int, db: Session = Depends(get_session)
) -> Response:
    try:
        statement_service.delete_cash_flow_statement(db, company_id, statement_id)
    except NotFoundError as exc:
        raise _to_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
