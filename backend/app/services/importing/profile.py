"""文档画像：可抽取性、准则、公司/年份线索。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from app.services.importing.text_utils import (
    guess_company_name,
    guess_stock_code,
    guess_years,
    to_simplified,
)


@dataclass
class DocumentProfile:
    path: str
    page_count: int
    extractability: float
    cjk_ratio: float
    cid_ratio: float
    table_hit_ratio: float
    standard: str  # CAS / US_GAAP / IFRS / unknown
    company_hint: str | None = None
    company_code_hint: str | None = None
    years: list[int] = field(default_factory=list)
    unit_scale: float = 1.0
    unit_confidence: float = 0.5
    sample_text: str = ""
    diagnostics: list[str] = field(default_factory=list)


def build_profile(pdf_path: Path, sample_pages: int = 25) -> DocumentProfile:
    path = Path(pdf_path)
    with pdfplumber.open(path) as doc:
        n = len(doc.pages)
        idxs = list(range(min(sample_pages, n)))
        # 也抽样尾部报表区
        if n > 80:
            idxs += list(range(max(0, n // 3), max(0, n // 3) + 5))
            idxs += list(range(max(0, n - 30), n))
        idxs = sorted(set(i for i in idxs if 0 <= i < n))

        texts: list[str] = []
        table_pages = 0
        for i in idxs:
            page = doc.pages[i]
            t = page.extract_text() or ""
            texts.append(t)
            tables = page.extract_tables() or []
            if any(tb and len(tb) >= 3 for tb in tables):
                table_pages += 1

        blob = "\n".join(texts)
        # 全文过贵；另取首页+目录增强公司名
        head = (doc.pages[0].extract_text() or "") if n else ""
        blob_for_meta = head + "\n" + blob

    total_chars = max(len(blob), 1)
    cjk = sum(1 for ch in blob if "\u4e00" <= ch <= "\u9fff")
    cjk_ratio = cjk / total_chars
    cid_ratio = blob.lower().count("cid:") / total_chars
    # 乱码控制符
    ctrl = sum(1 for ch in blob if ord(ch) < 32 and ch not in "\n\r\t")
    cid_ratio += ctrl / total_chars
    table_hit = table_pages / max(len(idxs), 1)
    digit_ratio = sum(ch.isdigit() for ch in blob) / total_chars

    diagnostics: list[str] = []
    if cid_ratio > 0.02 or (cjk_ratio < 0.15 and total_chars > 500):
        extractability = 0.1
        diagnostics.append("文本抽取质量差（CID/乱码），不适合自动解析")
    elif table_hit > 0.05 and cjk_ratio > 0.3:
        extractability = 0.9
    elif cjk_ratio > 0.3 and digit_ratio > 0.05:
        extractability = 0.65
        diagnostics.append("文本可抽取但表格可能不稳定，将启用行解析兜底")
    else:
        extractability = 0.35
        diagnostics.append("可抽取性一般")

    # 元数据（公司/代码/年份）优先封面与前几页，避免释义表/关联方名称污染
    cover_blob = to_simplified(
        "\n".join(
            [
                head,
                texts[1] if len(texts) > 1 else "",
                texts[2] if len(texts) > 2 else "",
                texts[3] if len(texts) > 3 else "",
            ]
        )
    )
    simplified = to_simplified(blob_for_meta)
    standard = "unknown"
    if any(k in simplified for k in ("合并资产负债表", "币种：人民币", "√适用", "不适用")):
        standard = "CAS"
    if any(k in simplified for k in ("美国公认会计原则", "美国公认会计準则", "美利坚合众国的公认会计")):
        standard = "US_GAAP"
    if "国际财务报告准则" in simplified or "IFRS" in blob_for_meta.upper():
        if standard == "unknown":
            standard = "IFRS"

    unit_scale = 1.0
    unit_confidence = 0.5
    if any(k in simplified for k in ("以千元为单位", "金额以千元", "千元为单位", "单位：千元")):
        unit_scale = 1000.0
        unit_confidence = 0.9
    elif any(k in simplified for k in ("百万元", "以百万元", "单位：百万元")):
        unit_scale = 1_000_000.0
        unit_confidence = 0.9
    elif "单位：元" in simplified or "单位:元" in simplified.replace(" ", ""):
        unit_scale = 1.0
        unit_confidence = 0.9

    company = guess_company_name(cover_blob) or guess_company_name(simplified)
    code = guess_stock_code(cover_blob) or guess_stock_code(simplified)
    # 年份：封面标题优先，再回退抽样全文
    years = guess_years(cover_blob) or guess_years(simplified)

    return DocumentProfile(
        path=str(path),
        page_count=n,
        extractability=extractability,
        cjk_ratio=cjk_ratio,
        cid_ratio=cid_ratio,
        table_hit_ratio=table_hit,
        standard=standard,
        company_hint=company,
        company_code_hint=code,
        years=years,
        unit_scale=unit_scale,
        unit_confidence=unit_confidence,
        sample_text=simplified[:2000],
        diagnostics=diagnostics,
    )
