"""资产负债表（BalanceSheet）ORM 模型。

CAS-simplified-v2 科目，见 openspec/changes/004-coa-v2-disclosure-layers/design.md。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _money(comment: str) -> Mapped[float | None]:
    return mapped_column(Numeric(18, 2), nullable=True, comment=comment)


class BalanceSheet(Base):
    """资产负债表：一行 = 一家企业的一个报告期。"""

    __tablename__ = "balance_sheets"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "year",
            "period_type",
            "quarter",
            name="uq_balance_sheet_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="年份")
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="annual / quarterly"
    )
    quarter: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="季报季度(1-4)，年报为空"
    )

    # —— 流动资产 ——
    monetary_funds: Mapped[float | None] = _money("货币资金")
    trading_financial_assets: Mapped[float | None] = _money("交易性金融资产")
    notes_receivable: Mapped[float | None] = _money("应收票据")
    accounts_receivable: Mapped[float | None] = _money("应收账款")
    prepayments: Mapped[float | None] = _money("预付款项")
    other_receivables: Mapped[float | None] = _money("其他应收款")
    inventories: Mapped[float | None] = _money("存货")
    other_current_assets: Mapped[float | None] = _money("其他流动资产")
    total_current_assets: Mapped[float | None] = _money("流动资产合计")

    # —— 非流动资产 ——
    long_term_equity_investments: Mapped[float | None] = _money("长期股权投资")
    other_equity_instruments_investment: Mapped[float | None] = _money("其他权益工具投资")
    other_non_current_financial_assets: Mapped[float | None] = _money(
        "其他非流动金融资产"
    )
    investment_property: Mapped[float | None] = _money("投资性房地产")
    fixed_assets: Mapped[float | None] = _money("固定资产")
    construction_in_progress: Mapped[float | None] = _money("在建工程")
    right_of_use_assets: Mapped[float | None] = _money("使用权资产")
    intangible_assets: Mapped[float | None] = _money("无形资产")
    goodwill: Mapped[float | None] = _money("商誉")
    deferred_tax_assets: Mapped[float | None] = _money("递延所得税资产")
    other_non_current_assets: Mapped[float | None] = _money("其他非流动资产")
    total_non_current_assets: Mapped[float | None] = _money("非流动资产合计")
    total_assets: Mapped[float | None] = _money("资产总计")

    # —— 流动负债 ——
    short_term_borrowings: Mapped[float | None] = _money("短期借款")
    notes_payable: Mapped[float | None] = _money("应付票据")
    accounts_payable: Mapped[float | None] = _money("应付账款")
    contract_liabilities: Mapped[float | None] = _money("合同负债")
    employee_benefits_payable: Mapped[float | None] = _money("应付职工薪酬")
    taxes_payable: Mapped[float | None] = _money("应交税费")
    other_payables: Mapped[float | None] = _money("其他应付款")
    non_current_liab_due_one_year: Mapped[float | None] = _money(
        "一年内到期的非流动负债"
    )
    other_current_liabilities: Mapped[float | None] = _money("其他流动负债")
    total_current_liabilities: Mapped[float | None] = _money("流动负债合计")

    # —— 非流动负债 / 负债合计 ——
    long_term_borrowings: Mapped[float | None] = _money("长期借款")
    bonds_payable: Mapped[float | None] = _money("应付债券")
    lease_liabilities: Mapped[float | None] = _money("租赁负债")
    deferred_income: Mapped[float | None] = _money("递延收益")
    deferred_tax_liabilities: Mapped[float | None] = _money("递延所得税负债")
    other_non_current_liabilities: Mapped[float | None] = _money("其他非流动负债")
    total_non_current_liabilities: Mapped[float | None] = _money("非流动负债合计")
    total_liabilities: Mapped[float | None] = _money("负债合计")

    # —— 所有者权益 ——
    paid_in_capital: Mapped[float | None] = _money("实收资本（或股本）")
    capital_reserve: Mapped[float | None] = _money("资本公积")
    treasury_stock: Mapped[float | None] = _money("库存股")
    other_comprehensive_income_equity: Mapped[float | None] = _money(
        "其他综合收益（权益）"
    )
    surplus_reserve: Mapped[float | None] = _money("盈余公积")
    retained_earnings: Mapped[float | None] = _money("未分配利润")
    total_equity_parent: Mapped[float | None] = _money("归属于母公司所有者权益合计")
    minority_interest: Mapped[float | None] = _money("少数股东权益")
    total_equity: Mapped[float | None] = _money("所有者权益合计")
