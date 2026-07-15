"""三大报表 Pydantic 校验模型。

报告期规则：
- period_type ∈ {annual, quarterly}
- annual → quarter 必须为 None
- quarterly → quarter ∈ {1,2,3,4}
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import (
    PERIOD_ANNUAL,
    PERIOD_QUARTERLY,
    QUARTERS,
    YEAR_MAX,
    YEAR_MIN,
)

Money = Annotated[float | None, Field(default=None)]
PeriodType = Literal["annual", "quarterly"]


class PeriodMixin(BaseModel):
    """报告期字段 + 校验。"""

    year: int = Field(..., ge=YEAR_MIN, le=YEAR_MAX, description="年份")
    period_type: PeriodType = Field(..., description="annual / quarterly")
    quarter: int | None = Field(default=None, description="季报季度 1-4，年报为空")

    @field_validator("quarter")
    @classmethod
    def quarter_range(cls, v: int | None) -> int | None:
        if v is not None and v not in QUARTERS:
            raise ValueError(f"季度必须是 {list(QUARTERS)} 之一")
        return v

    @model_validator(mode="after")
    def period_consistency(self) -> PeriodMixin:
        if self.period_type == PERIOD_ANNUAL:
            if self.quarter is not None:
                raise ValueError("年报（annual）的 quarter 必须为空")
        elif self.period_type == PERIOD_QUARTERLY:
            if self.quarter is None:
                raise ValueError("季报（quarterly）必须指定 quarter（1-4）")
        return self


class PeriodUpdateMixin(BaseModel):
    """部分更新时的报告期字段（均可选，但若给出需自洽）。"""

    year: int | None = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    period_type: PeriodType | None = None
    quarter: int | None = None

    @field_validator("quarter")
    @classmethod
    def quarter_range(cls, v: int | None) -> int | None:
        if v is not None and v not in QUARTERS:
            raise ValueError(f"季度必须是 {list(QUARTERS)} 之一")
        return v


# ---------------------------------------------------------------------------
# 资产负债表
# ---------------------------------------------------------------------------


class BalanceSheetCreate(PeriodMixin):
    monetary_funds: Money = None
    trading_financial_assets: Money = None
    notes_receivable: Money = None
    accounts_receivable: Money = None
    prepayments: Money = None
    other_receivables: Money = None
    inventories: Money = None
    other_current_assets: Money = None
    total_current_assets: Money = None
    long_term_equity_investments: Money = None
    other_equity_instruments_investment: Money = None
    other_non_current_financial_assets: Money = None
    investment_property: Money = None
    fixed_assets: Money = None
    construction_in_progress: Money = None
    right_of_use_assets: Money = None
    intangible_assets: Money = None
    goodwill: Money = None
    deferred_tax_assets: Money = None
    other_non_current_assets: Money = None
    total_non_current_assets: Money = None
    total_assets: Money = None
    short_term_borrowings: Money = None
    notes_payable: Money = None
    accounts_payable: Money = None
    contract_liabilities: Money = None
    employee_benefits_payable: Money = None
    taxes_payable: Money = None
    other_payables: Money = None
    non_current_liab_due_one_year: Money = None
    other_current_liabilities: Money = None
    total_current_liabilities: Money = None
    long_term_borrowings: Money = None
    bonds_payable: Money = None
    lease_liabilities: Money = None
    deferred_income: Money = None
    deferred_tax_liabilities: Money = None
    other_non_current_liabilities: Money = None
    total_non_current_liabilities: Money = None
    total_liabilities: Money = None
    paid_in_capital: Money = None
    capital_reserve: Money = None
    treasury_stock: Money = None
    other_comprehensive_income_equity: Money = None
    surplus_reserve: Money = None
    retained_earnings: Money = None
    total_equity_parent: Money = None
    minority_interest: Money = None
    total_equity: Money = None


class BalanceSheetUpdate(PeriodUpdateMixin):
    monetary_funds: Money = None
    trading_financial_assets: Money = None
    notes_receivable: Money = None
    accounts_receivable: Money = None
    prepayments: Money = None
    other_receivables: Money = None
    inventories: Money = None
    other_current_assets: Money = None
    total_current_assets: Money = None
    long_term_equity_investments: Money = None
    other_equity_instruments_investment: Money = None
    other_non_current_financial_assets: Money = None
    investment_property: Money = None
    fixed_assets: Money = None
    construction_in_progress: Money = None
    right_of_use_assets: Money = None
    intangible_assets: Money = None
    goodwill: Money = None
    deferred_tax_assets: Money = None
    other_non_current_assets: Money = None
    total_non_current_assets: Money = None
    total_assets: Money = None
    short_term_borrowings: Money = None
    notes_payable: Money = None
    accounts_payable: Money = None
    contract_liabilities: Money = None
    employee_benefits_payable: Money = None
    taxes_payable: Money = None
    other_payables: Money = None
    non_current_liab_due_one_year: Money = None
    other_current_liabilities: Money = None
    total_current_liabilities: Money = None
    long_term_borrowings: Money = None
    bonds_payable: Money = None
    lease_liabilities: Money = None
    deferred_income: Money = None
    deferred_tax_liabilities: Money = None
    other_non_current_liabilities: Money = None
    total_non_current_liabilities: Money = None
    total_liabilities: Money = None
    paid_in_capital: Money = None
    capital_reserve: Money = None
    treasury_stock: Money = None
    other_comprehensive_income_equity: Money = None
    surplus_reserve: Money = None
    retained_earnings: Money = None
    total_equity_parent: Money = None
    minority_interest: Money = None
    total_equity: Money = None


class BalanceSheetRead(BalanceSheetCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int


# ---------------------------------------------------------------------------
# 利润表
# ---------------------------------------------------------------------------


class IncomeStatementCreate(PeriodMixin):
    operating_revenue: Money = None
    operating_cost: Money = None
    taxes_and_surcharges: Money = None
    selling_expenses: Money = None
    admin_expenses: Money = None
    rd_expenses: Money = None
    financial_expenses: Money = None
    interest_income: Money = None
    other_income: Money = None
    investment_income: Money = None
    fair_value_change_income: Money = None
    credit_impairment_loss: Money = None
    asset_impairment_loss: Money = None
    asset_disposal_income: Money = None
    operating_profit: Money = None
    non_operating_income: Money = None
    non_operating_expense: Money = None
    total_profit: Money = None
    income_tax_expense: Money = None
    net_profit: Money = None
    net_profit_parent: Money = None
    net_profit_minority: Money = None
    other_comprehensive_income: Money = None
    total_comprehensive_income: Money = None


class IncomeStatementUpdate(PeriodUpdateMixin):
    operating_revenue: Money = None
    operating_cost: Money = None
    taxes_and_surcharges: Money = None
    selling_expenses: Money = None
    admin_expenses: Money = None
    rd_expenses: Money = None
    financial_expenses: Money = None
    interest_income: Money = None
    other_income: Money = None
    investment_income: Money = None
    fair_value_change_income: Money = None
    credit_impairment_loss: Money = None
    asset_impairment_loss: Money = None
    asset_disposal_income: Money = None
    operating_profit: Money = None
    non_operating_income: Money = None
    non_operating_expense: Money = None
    total_profit: Money = None
    income_tax_expense: Money = None
    net_profit: Money = None
    net_profit_parent: Money = None
    net_profit_minority: Money = None
    other_comprehensive_income: Money = None
    total_comprehensive_income: Money = None


class IncomeStatementRead(IncomeStatementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int


# ---------------------------------------------------------------------------
# 现金流量表
# ---------------------------------------------------------------------------


class CashFlowStatementCreate(PeriodMixin):
    cash_from_sales: Money = None
    tax_refunds_received: Money = None
    other_cash_received_operating: Money = None
    cash_paid_for_goods: Money = None
    cash_paid_to_employees: Money = None
    taxes_paid: Money = None
    other_cash_paid_operating: Money = None
    net_cash_flow_operating: Money = None
    cash_from_investments: Money = None
    cash_from_investment_income: Money = None
    cash_from_asset_disposal: Money = None
    cash_paid_for_assets: Money = None
    cash_paid_for_investments: Money = None
    net_cash_flow_investing: Money = None
    cash_from_financing: Money = None
    cash_paid_for_debt: Money = None
    cash_paid_for_dividends: Money = None
    net_cash_flow_financing: Money = None
    net_increase_in_cash: Money = None


class CashFlowStatementUpdate(PeriodUpdateMixin):
    cash_from_sales: Money = None
    tax_refunds_received: Money = None
    other_cash_received_operating: Money = None
    cash_paid_for_goods: Money = None
    cash_paid_to_employees: Money = None
    taxes_paid: Money = None
    other_cash_paid_operating: Money = None
    net_cash_flow_operating: Money = None
    cash_from_investments: Money = None
    cash_from_investment_income: Money = None
    cash_from_asset_disposal: Money = None
    cash_paid_for_assets: Money = None
    cash_paid_for_investments: Money = None
    net_cash_flow_investing: Money = None
    cash_from_financing: Money = None
    cash_paid_for_debt: Money = None
    cash_paid_for_dividends: Money = None
    net_cash_flow_financing: Money = None
    net_increase_in_cash: Money = None


class CashFlowStatementRead(CashFlowStatementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int


# 导出
__all__ = [
    "BalanceSheetCreate",
    "BalanceSheetUpdate",
    "BalanceSheetRead",
    "IncomeStatementCreate",
    "IncomeStatementUpdate",
    "IncomeStatementRead",
    "CashFlowStatementCreate",
    "CashFlowStatementUpdate",
    "CashFlowStatementRead",
]
