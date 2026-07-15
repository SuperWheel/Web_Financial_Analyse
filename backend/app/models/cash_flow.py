"""现金流量表（CashFlowStatement）ORM 模型。

CAS-simplified-v2 科目，见 openspec/changes/004-coa-v2-disclosure-layers/design.md。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _money(comment: str) -> Mapped[float | None]:
    return mapped_column(Numeric(18, 2), nullable=True, comment=comment)


class CashFlowStatement(Base):
    """现金流量表：一行 = 一家企业的一个报告期。"""

    __tablename__ = "cash_flow_statements"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "year",
            "period_type",
            "quarter",
            name="uq_cash_flow_statement_period",
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

    cash_from_sales: Mapped[float | None] = _money("销售商品、提供劳务收到的现金")
    tax_refunds_received: Mapped[float | None] = _money("收到的税费返还")
    other_cash_received_operating: Mapped[float | None] = _money(
        "收到其他与经营活动有关的现金"
    )
    cash_paid_for_goods: Mapped[float | None] = _money("购买商品、接受劳务支付的现金")
    cash_paid_to_employees: Mapped[float | None] = _money(
        "支付给职工以及为职工支付的现金"
    )
    taxes_paid: Mapped[float | None] = _money("支付的各项税费")
    other_cash_paid_operating: Mapped[float | None] = _money(
        "支付其他与经营活动有关的现金"
    )
    net_cash_flow_operating: Mapped[float | None] = _money(
        "经营活动产生的现金流量净额"
    )
    cash_from_investments: Mapped[float | None] = _money("收回投资收到的现金")
    cash_from_investment_income: Mapped[float | None] = _money("取得投资收益收到的现金")
    cash_from_asset_disposal: Mapped[float | None] = _money(
        "处置固定资产等收回的现金净额"
    )
    cash_paid_for_assets: Mapped[float | None] = _money("购建固定资产等支付的现金")
    cash_paid_for_investments: Mapped[float | None] = _money("投资支付的现金")
    net_cash_flow_investing: Mapped[float | None] = _money(
        "投资活动产生的现金流量净额"
    )
    cash_from_financing: Mapped[float | None] = _money(
        "吸收投资/取得借款收到的现金"
    )
    cash_paid_for_debt: Mapped[float | None] = _money("偿还债务支付的现金")
    cash_paid_for_dividends: Mapped[float | None] = _money(
        "分配股利、利润或偿付利息支付的现金"
    )
    net_cash_flow_financing: Mapped[float | None] = _money(
        "筹资活动产生的现金流量净额"
    )
    net_increase_in_cash: Mapped[float | None] = _money("现金及现金等价物净增加额")
