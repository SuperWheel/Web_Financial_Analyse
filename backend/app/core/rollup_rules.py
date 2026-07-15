"""显式归并规则：源标签 → 标准科目（仅 alias 未命中时）。

禁止模糊相似度静默匹配；规则必须可审阅、可单测。
"""
from __future__ import annotations

from typing import TypedDict


class RollupRule(TypedDict):
    patterns: list[str]
    mapped_to: str
    statement: str
    note: str


# 匹配前对 label / pattern 做 normalize_label
ROLLUP_RULES: list[RollupRule] = [
    {
        "patterns": ["衍生金融资产", "衍生金融资产净额"],
        "mapped_to": "trading_financial_assets",
        "statement": "balance",
        "note": "常见并入交易性/以公允价值计量金融资产",
    },
    {
        "patterns": ["应收股利", "应收利息"],
        "mapped_to": "other_receivables",
        "statement": "balance",
        "note": "并入其他应收款",
    },
    {
        "patterns": ["债权投资", "债权投资净额"],
        "mapped_to": "other_non_current_assets",
        "statement": "balance",
        "note": "未单独升格时进其他非流动资产",
    },
    {
        "patterns": ["预计负债"],
        "mapped_to": "other_non_current_liabilities",
        "statement": "balance",
        "note": "并入其他非流动负债桶",
    },
    {
        "patterns": ["合同资产", "合同资产净额"],
        "mapped_to": "other_current_assets",
        "statement": "balance",
        "note": "未单独升格；可后续升格",
    },
    {
        "patterns": ["长期待摊费用"],
        "mapped_to": "other_non_current_assets",
        "statement": "balance",
        "note": "并入其他非流动资产",
    },
    {
        "patterns": ["收到其他与投资活动有关的现金"],
        "mapped_to": "cash_from_investments",
        "statement": "cashflow",
        "note": "弱归并；完整明细仍可在 L0",
    },
    {
        "patterns": ["支付其他与投资活动有关的现金"],
        "mapped_to": "cash_paid_for_investments",
        "statement": "cashflow",
        "note": "弱归并",
    },
    {
        "patterns": ["收到其他与筹资活动有关的现金"],
        "mapped_to": "cash_from_financing",
        "statement": "cashflow",
        "note": "弱归并",
    },
    {
        "patterns": ["支付其他与筹资活动有关的现金"],
        "mapped_to": "cash_paid_for_debt",
        "statement": "cashflow",
        "note": "弱归并至筹资流出代表项",
    },
]


def match_rollup(statement: str, label_norm: str) -> RollupRule | None:
    """精确或规范化相等匹配；不使用模糊包含（避免误伤）。"""
    if not label_norm:
        return None
    for rule in ROLLUP_RULES:
        if rule["statement"] != statement:
            continue
        for p in rule["patterns"]:
            # 延迟 import 避免循环
            from app.services.importing.text_utils import normalize_label

            if label_norm == normalize_label(p):
                return rule
    return None
