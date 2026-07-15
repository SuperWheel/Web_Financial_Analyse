"""科目别名词典：源表标签 → 系统字段。

匹配前会做繁简转换与清洗，因此这里以简体为主，可附常见变体。
"""
from __future__ import annotations

from typing import TypedDict


class AliasEntry(TypedDict, total=False):
    aliases: list[str]
    priority: int
    tags: list[str]  # core / total
    contexts: list[str]


# statement -> field -> entry
SUBJECT_ALIASES: dict[str, dict[str, AliasEntry]] = {
    "balance": {
        "monetary_funds": {
            "aliases": ["货币资金", "现金及现金等价物", "现金", "库存现金"],
            "priority": 100,
            "tags": ["core"],
        },
        "trading_financial_assets": {
            "aliases": [
                "交易性金融资产",
                "短期投资",
                "以公允价值计量且其变动计入当期损益的金融资产",
            ],
            "priority": 80,
        },
        "notes_receivable": {"aliases": ["应收票据"], "priority": 90},
        "accounts_receivable": {
            "aliases": ["应收账款", "应收账款净额", "应收帐款", "应收款项"],
            "priority": 100,
            "tags": ["core"],
        },
        "prepayments": {"aliases": ["预付款项", "预付账款", "预付帐款"], "priority": 90},
        "other_receivables": {
            "aliases": ["其他应收款", "其他应收款净额", "应收关联方款项"],
            "priority": 70,
        },
        "inventories": {"aliases": ["存货", "存货净额"], "priority": 100, "tags": ["core"]},
        "other_current_assets": {
            "aliases": ["其他流动资产", "预付款项及其他流动资产", "一年内到期的非流动资产"],
            "priority": 50,
        },
        "total_current_assets": {
            "aliases": ["流动资产合计", "流动资产总计", "流动资产总额"],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "long_term_equity_investments": {
            "aliases": ["长期股权投资", "长期投资", "长期投资净额"],
            "priority": 80,
        },
        "other_equity_instruments_investment": {
            "aliases": ["其他权益工具投资", "其他权益工具投资净额"],
            "priority": 85,
        },
        "other_non_current_financial_assets": {
            "aliases": ["其他非流动金融资产"],
            "priority": 85,
        },
        "investment_property": {
            "aliases": ["投资性房地产", "投资性房地产净额"],
            "priority": 85,
        },
        "fixed_assets": {
            "aliases": ["固定资产", "固定资产净额", "固定资产净值", "物业及设备", "物业及设备净额"],
            "priority": 90,
        },
        "construction_in_progress": {"aliases": ["在建工程"], "priority": 80},
        "right_of_use_assets": {
            "aliases": ["使用权资产", "使用权资产净额"],
            "priority": 90,
        },
        "intangible_assets": {
            "aliases": ["无形资产", "无形资产净额"],
            "priority": 80,
        },
        "goodwill": {"aliases": ["商誉"], "priority": 80},
        "deferred_tax_assets": {
            "aliases": ["递延所得税资产", "递延税项资产", "递延税款借项"],
            "priority": 80,
        },
        "other_non_current_assets": {
            "aliases": ["其他非流动资产", "其他长期资产", "长期待摊费用"],
            "priority": 50,
        },
        "total_non_current_assets": {
            "aliases": ["非流动资产合计", "非流动资产总计", "非流动资产总额"],
            "priority": 90,
            "tags": ["total"],
        },
        "total_assets": {
            "aliases": [
                "资产总计",
                "资产合计",
                "资产总额",
                "总资产",
                "负债和所有者权益总计",
                "负债及所有者权益总计",
                "负债和股东权益总计",
                "负债和所有者权益（或股东权益）总计",
                "负债和所有者权益(或股东权益)总计",
                "负债及股东权益总计",
            ],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "short_term_borrowings": {
            "aliases": ["短期借款", "短期贷款", "短期贷款及长期债务的即期部分"],
            "priority": 80,
        },
        "notes_payable": {"aliases": ["应付票据"], "priority": 80},
        "accounts_payable": {"aliases": ["应付账款", "应付帐款"], "priority": 90},
        "contract_liabilities": {
            "aliases": ["合同负债", "递延收入", "预收款项", "预收账款"],
            "priority": 70,
        },
        "employee_benefits_payable": {
            "aliases": ["应付职工薪酬", "应付薪资及福利", "应付工资"],
            "priority": 80,
        },
        "taxes_payable": {"aliases": ["应交税费", "应付税项", "应交税金"], "priority": 80},
        "other_payables": {
            "aliases": ["其他应付款", "其他应付款项"],
            "priority": 70,
        },
        "non_current_liab_due_one_year": {
            "aliases": [
                "一年内到期的非流动负债",
                "一年内到期的长期负债",
                "一年内到期的非流动负债净额",
            ],
            "priority": 80,
        },
        "other_current_liabilities": {
            "aliases": ["其他流动负债"],
            "priority": 80,
        },
        "total_current_liabilities": {
            "aliases": ["流动负债合计", "流动负债总计", "流动负债总额"],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "long_term_borrowings": {"aliases": ["长期借款", "长期贷款"], "priority": 80},
        "bonds_payable": {"aliases": ["应付债券"], "priority": 80},
        "lease_liabilities": {"aliases": ["租赁负债"], "priority": 70},
        "deferred_income": {
            "aliases": ["递延收益"],
            "priority": 75,
        },
        "deferred_tax_liabilities": {
            "aliases": ["递延所得税负债", "递延税项负债", "递延税款贷项"],
            "priority": 80,
        },
        "other_non_current_liabilities": {
            "aliases": ["其他非流动负债"],
            "priority": 70,
        },
        "total_non_current_liabilities": {
            "aliases": ["非流动负债合计", "非流动负债总计"],
            "priority": 90,
            "tags": ["total"],
        },
        "total_liabilities": {
            "aliases": ["负债合计", "负债总计", "负债总额"],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "paid_in_capital": {
            "aliases": [
                "实收资本（或股本）",
                "实收资本(或股本)",
                "实收资本",
                "股本",
                "注册资本",
            ],
            "priority": 95,
            "tags": ["core"],
        },
        "capital_reserve": {
            "aliases": ["资本公积"],
            "priority": 90,
            "tags": ["core"],
        },
        "treasury_stock": {
            "aliases": ["库存股", "减：库存股", "减:库存股"],
            "priority": 90,
        },
        "other_comprehensive_income_equity": {
            "aliases": [
                "其他综合收益",
                "其他综合收益（权益）",
                "其他综合收益余额",
            ],
            "priority": 80,
        },
        "surplus_reserve": {
            "aliases": ["盈余公积"],
            "priority": 90,
            "tags": ["core"],
        },
        "retained_earnings": {
            "aliases": ["未分配利润"],
            "priority": 90,
            "tags": ["core"],
        },
        "total_equity_parent": {
            "aliases": [
                "归属于母公司所有者权益合计",
                "归属于母公司股东权益合计",
                "归属于母公司所有者权益（或股东权益）合计",
                "归属于母公司所有者权益(或股东权益)合计",
                "归属于母公司股东权益（或所有者权益）合计",
            ],
            "priority": 95,
            "tags": ["total"],
        },
        "minority_interest": {
            "aliases": ["少数股东权益", "少数股东权益合计", "非控制性权益"],
            "priority": 95,
        },
        "total_equity": {
            "aliases": [
                "所有者权益合计",
                "股东权益合计",
                "所有者权益或股东权益合计",
                "所有者权益(或股东权益)合计",
                "所有者权益（或股东权益）合计",
            ],
            "priority": 100,
            "tags": ["core", "total"],
        },
    },
    "income": {
        "operating_revenue": {
            "aliases": [
                "营业收入",
                "其中：营业收入",
                "营业总收入",
                "净营业额",
                "主营业务收入",
                "一、营业收入",
                "一、营业总收入",
            ],
            "priority": 90,
            "tags": ["core"],
        },
        "operating_cost": {
            "aliases": ["营业成本", "减：营业成本", "其中：营业成本"],
            "priority": 85,
            "tags": ["core"],
        },
        "taxes_and_surcharges": {"aliases": ["税金及附加"], "priority": 80},
        "selling_expenses": {
            "aliases": ["销售费用", "销售及营销开支", "销售及营销费用"],
            "priority": 80,
        },
        "admin_expenses": {
            "aliases": ["管理费用", "一般及行政开支", "一般及行政费用"],
            "priority": 80,
        },
        "rd_expenses": {"aliases": ["研发费用", "研发开支"], "priority": 80},
        "financial_expenses": {"aliases": ["财务费用"], "priority": 80},
        "interest_income": {
            "aliases": ["利息收入", "其中：利息收入"],
            "priority": 75,
        },
        "other_income": {"aliases": ["其他收益", "加：其他收益"], "priority": 70},
        "investment_income": {"aliases": ["投资收益"], "priority": 70},
        "fair_value_change_income": {
            "aliases": [
                "公允价值变动收益",
                "公允价值变动收益（损失以“－”号填列）",
                "公允价值变动收益(损失以“－”号填列)",
                "公允价值变动收益（损失以“-”号填列）",
            ],
            "priority": 85,
        },
        "credit_impairment_loss": {"aliases": ["信用减值损失"], "priority": 70},
        "asset_impairment_loss": {"aliases": ["资产减值损失"], "priority": 70},
        "asset_disposal_income": {
            "aliases": [
                "资产处置收益",
                "资产处置收益（损失以“－”号填列）",
                "资产处置收益(损失以“－”号填列)",
                "资产处置收益（损失以“-”号填列）",
            ],
            "priority": 85,
        },
        "operating_profit": {
            "aliases": ["营业利润", "二、营业利润", "三、营业利润"],
            "priority": 90,
            "tags": ["total"],
        },
        "non_operating_income": {
            "aliases": ["营业外收入", "加：营业外收入"],
            "priority": 80,
        },
        "non_operating_expense": {
            "aliases": ["营业外支出", "减：营业外支出"],
            "priority": 80,
        },
        "total_profit": {
            "aliases": ["利润总额", "三、利润总额", "四、利润总额"],
            "priority": 90,
            "tags": ["total"],
        },
        "income_tax_expense": {
            "aliases": ["所得税费用", "减：所得税费用"],
            "priority": 85,
        },
        "net_profit": {
            "aliases": [
                "净利润",
                "四、净利润",
                "五、净利润",
                "净利润（净亏损以“-”号填列）",
                "净利润（净亏损以“－”号填列）",
            ],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "net_profit_parent": {
            "aliases": [
                "归属于母公司股东的净利润",
                "归属于母公司所有者的净利润",
                "归属于母公司股东的净利润（净亏损以“-”号填列）",
                "1.归属于母公司股东的净利润",
                "1．归属于母公司股东的净利润",
            ],
            "priority": 95,
        },
        "net_profit_minority": {
            "aliases": [
                "少数股东损益",
                "2.少数股东损益",
                "2．少数股东损益",
                "少数股东损益（净亏损以“-”号填列）",
            ],
            "priority": 95,
        },
        "other_comprehensive_income": {
            "aliases": [
                "其他综合收益",
                "五、其他综合收益",
                "其他综合收益的税后净额",
            ],
            "priority": 70,
        },
        "total_comprehensive_income": {
            "aliases": [
                "综合收益总额",
                "六、综合收益总额",
                "七、综合收益总额",
            ],
            "priority": 90,
            "tags": ["total"],
        },
    },
    "cashflow": {
        "cash_from_sales": {
            "aliases": [
                "销售商品、提供劳务收到的现金",
                "销售商品提供劳务收到的现金",
            ],
            "priority": 90,
        },
        "tax_refunds_received": {
            "aliases": ["收到的税费返还"],
            "priority": 85,
        },
        "other_cash_received_operating": {
            "aliases": ["收到其他与经营活动有关的现金"],
            "priority": 90,
        },
        "cash_paid_for_goods": {
            "aliases": [
                "购买商品、接受劳务支付的现金",
                "购买商品接受劳务支付的现金",
            ],
            "priority": 90,
        },
        "cash_paid_to_employees": {
            "aliases": ["支付给职工以及为职工支付的现金"],
            "priority": 90,
        },
        "taxes_paid": {"aliases": ["支付的各项税费"], "priority": 90},
        "other_cash_paid_operating": {
            "aliases": ["支付其他与经营活动有关的现金"],
            "priority": 90,
        },
        "net_cash_flow_operating": {
            "aliases": [
                "经营活动产生的现金流量净额",
                "经营活动产生的现金流净额",
            ],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "cash_from_investments": {"aliases": ["收回投资收到的现金"], "priority": 80},
        "cash_from_investment_income": {
            "aliases": ["取得投资收益收到的现金"],
            "priority": 85,
        },
        "cash_from_asset_disposal": {
            "aliases": [
                "处置固定资产、无形资产和其他长期资产收回的现金净额",
                "处置固定资产等收回的现金净额",
            ],
            "priority": 80,
        },
        "cash_paid_for_assets": {
            "aliases": [
                "购建固定资产、无形资产和其他长期资产支付的现金",
                "购建固定资产等支付的现金",
                "购买物业及设备",
            ],
            "priority": 80,
        },
        "cash_paid_for_investments": {"aliases": ["投资支付的现金"], "priority": 80},
        "net_cash_flow_investing": {
            "aliases": ["投资活动产生的现金流量净额", "投资活动产生的现金流净额"],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "cash_from_financing": {
            "aliases": [
                "吸收投资收到的现金",
                "取得借款收到的现金",
                "吸收投资/取得借款收到的现金",
            ],
            "priority": 70,
        },
        "cash_paid_for_debt": {"aliases": ["偿还债务支付的现金"], "priority": 80},
        "cash_paid_for_dividends": {
            "aliases": [
                "分配股利、利润或偿付利息支付的现金",
                "分配股利或利润或偿付利息所支付的现金",
            ],
            "priority": 80,
        },
        "net_cash_flow_financing": {
            "aliases": ["筹资活动产生的现金流量净额", "筹资活动产生的现金流净额"],
            "priority": 100,
            "tags": ["core", "total"],
        },
        "net_increase_in_cash": {
            "aliases": [
                "现金及现金等价物净增加额",
                "五、现金及现金等价物净增加额",
            ],
            "priority": 100,
            "tags": ["core", "total"],
        },
    },
}

# 核心闸门字段
CORE_FIELDS: dict[str, tuple[str, ...]] = {
    "balance": (
        "monetary_funds",
        "accounts_receivable",
        "inventories",
        "total_current_assets",
        "total_assets",
        "total_current_liabilities",
        "total_liabilities",
        "total_equity",
        "paid_in_capital",
        "retained_earnings",
    ),
    "income": ("operating_revenue", "operating_cost", "net_profit"),
    "cashflow": ("net_cash_flow_operating",),
}
