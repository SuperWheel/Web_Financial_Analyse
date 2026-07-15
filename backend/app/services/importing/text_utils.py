"""文本清洗与金额解析。"""
from __future__ import annotations

import re
from functools import lru_cache

_AMOUNT_RE = re.compile(
    r"[（(]?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*[)）]?|—|–|－"
)
_ONLY_AMOUNT_RE = re.compile(
    r"^\s*[（(]?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*[)）]?\s*$"
)


@lru_cache(maxsize=1)
def _t2s():
    try:
        from opencc import OpenCC

        return OpenCC("t2s")
    except Exception:  # pragma: no cover
        return None


def to_simplified(text: str) -> str:
    if not text:
        return ""
    cc = _t2s()
    if cc is None:
        return text
    return cc.convert(text)


def normalize_label(label: str) -> str:
    """科目标签规范化：繁简、去噪声、压空白。"""
    s = to_simplified(label or "")
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    s = re.sub(r"[\r\n\t]+", "", s)
    s = s.replace("（", "(").replace("）", ")")
    # 行号/章节号
    s = re.sub(r"^[0-9]+[\.、．]", "", s)
    s = re.sub(r"^[一二三四五六七八九十百]+[、.．]", "", s)
    # 尾部填列说明
    s = re.sub(r"[（(]净亏损以.*?[)）]", "", s)
    s = re.sub(r"[（(]亏损以.*?[)）]", "", s)
    s = re.sub(r'以["“]-["”]号填列', "", s)
    s = re.sub(r"[（(]净额[)）]", "", s)
    s = re.sub(r"[（(]淨額[)）]", "", s)
    s = re.sub(r"\s+", "", s)
    # 统一斜杠
    s = s.replace("╱", "/").replace("／", "/")
    return s.strip()


def normalize_title(text: str) -> str:
    s = normalize_label(text)
    return s.lower() if s.isascii() else s


def parse_amount(raw: str | None) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in {"—", "–", "－", "-", "— —", "/"}:
        return None
    neg = False
    if (s.startswith("(") and s.endswith(")")) or (
        s.startswith("（") and s.endswith("）")
    ):
        neg = True
        s = s[1:-1].strip()
    if s.startswith("-") or s.startswith("－"):
        neg = True
        s = s[1:].strip()
    s = s.replace(",", "").replace("，", "").replace(" ", "")
    s = re.sub(r"[￥¥$USD人民币RMB元]", "", s, flags=re.I)
    if not s:
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    return -abs(val) if neg else val


def extract_amounts(text: str) -> list[float]:
    """从一行中提取全部金额（保持顺序）。"""
    out: list[float] = []
    for m in _AMOUNT_RE.finditer(text or ""):
        token = m.group(0)
        if token in {"—", "–", "－"}:
            continue
        # 跳过过短纯整数年份误伤：4 位整数且像年份
        cleaned = token.replace(",", "").strip("()（） ")
        if re.fullmatch(r"20\d{2}", cleaned):
            continue
        amt = parse_amount(token)
        if amt is not None:
            out.append(amt)
    return out


def is_section_label(label: str, amount: float | None) -> bool:
    if amount is not None:
        return False
    s = (label or "").strip()
    if not s:
        return True
    if s.endswith("：") or s.endswith(":"):
        return True
    if re.match(r"^[一二三四五六七八九十]+[、.]", s):
        return True
    return False


def is_total_label(label: str) -> bool:
    s = normalize_label(label)
    return any(k in s for k in ("合计", "总计", "总额", "净额", "净增加额"))


_COMPANY_RE = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9（）()]{2,40}(?:股份有限公司|有限公司|集团|集團))"
)
_CODE_RE = re.compile(
    r"(?:股票代码|证券代码|股份代号|股份代號|港交所代号|港交所代號|证券代号)[:：\s]*([0-9A-Za-z.]{3,10})",
    re.I,
)
_YEAR_RE = re.compile(r"(20\d{2})\s*年")


def guess_company_name(text: str) -> str | None:
    # 编制单位优先
    m = re.search(r"编制单位[:：]\s*([^\n]{2,60})", text)
    if m:
        name = m.group(1).strip()
        name = re.split(r"\s{2,}|单位", name)[0].strip()
        if len(name) >= 4:
            return to_simplified(name)
    hits = _COMPANY_RE.findall(text[:3000])
    if not hits:
        return None
    # 最长且含「股份」优先
    hits = sorted(set(hits), key=lambda x: (0 if "股份" in x else 1, -len(x)))
    return to_simplified(hits[0])


def guess_stock_code(text: str) -> str | None:
    m = _CODE_RE.search(text[:4000])
    return m.group(1) if m else None


def guess_years(text: str) -> list[int]:
    years = [int(y) for y in _YEAR_RE.findall(text)]
    # 也抓表头 2025年12月31日
    years += [int(y) for y in re.findall(r"(20\d{2})年\d{1,2}月", text)]
    # unique keep order desc
    seen: list[int] = []
    for y in sorted(set(years), reverse=True):
        if 1990 <= y <= 2100:
            seen.append(y)
    return seen
