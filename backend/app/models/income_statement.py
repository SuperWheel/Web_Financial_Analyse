"""利润表（IncomeStatement）ORM 模型。

CAS-simplified-v2 科目，见 openspec/changes/004-coa-v2-disclosure-layers/design.md。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _money(comment: str) -> Mapped[float | None]:
    return mapped_column(Numeric(18, 2), nullable=True, comment=comment)


class IncomeStatement(Base):
    """利润表：一行 = 一家企业的一个报告期。"""

    __tablename__ = "income_statements"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "year",
            "period_type",
            "quarter",
            name="uq_income_statement_period",
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

    operating_revenue: Mapped[float | None] = _money("营业收入")
    operating_cost: Mapped[float | None] = _money("营业成本")
    taxes_and_surcharges: Mapped[float | None] = _money("税金及附加")
    selling_expenses: Mapped[float | None] = _money("销售费用")
    admin_expenses: Mapped[float | None] = _money("管理费用")
    rd_expenses: Mapped[float | None] = _money("研发费用")
    financial_expenses: Mapped[float | None] = _money("财务费用")
    interest_income: Mapped[float | None] = _money("利息收入")
    other_income: Mapped[float | None] = _money("其他收益")
    investment_income: Mapped[float | None] = _money("投资收益")
    fair_value_change_income: Mapped[float | None] = _money("公允价值变动收益")
    credit_impairment_loss: Mapped[float | None] = _money("信用减值损失")
    asset_impairment_loss: Mapped[float | None] = _money("资产减值损失")
    asset_disposal_income: Mapped[float | None] = _money("资产处置收益")
    operating_profit: Mapped[float | None] = _money("营业利润")
    non_operating_income: Mapped[float | None] = _money("营业外收入")
    non_operating_expense: Mapped[float | None] = _money("营业外支出")
    total_profit: Mapped[float | None] = _money("利润总额")
    income_tax_expense: Mapped[float | None] = _money("所得税费用")
    net_profit: Mapped[float | None] = _money("净利润")
    net_profit_parent: Mapped[float | None] = _money("归属于母公司股东的净利润")
    net_profit_minority: Mapped[float | None] = _money("少数股东损益")
    other_comprehensive_income: Mapped[float | None] = _money("其他综合收益")
    total_comprehensive_income: Mapped[float | None] = _money("综合收益总额")
