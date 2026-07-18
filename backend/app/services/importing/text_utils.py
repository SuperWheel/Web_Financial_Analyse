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
    r"(?:股票代码|证券代码|公司代码|股份代号|股份代號|港交所代号|港交所代號|证券代号)[:：\s]*([0-9A-Za-z.]{3,10})",
    re.I,
)
_YEAR_RE = re.compile(r"(20\d{2})\s*年")
_GLOSSARY_LINE_RE = re.compile(r"^\s*\S.{0,20}\s+指\s+")


def guess_company_name(text: str) -> str | None:
    """从年报文本推断发行人名称。

    优先封面/法定名称字段；避免释义表（「红旗连锁 指 成都红旗…」）误伤。
    """
    if not text:
        return None
    t = text

    # 1) 法定中文名称（年报常见）
    for pat in (
        r"公司的中文名称\s*[:：]?\s*([^\n]{4,80})",
        r"中文名称\s*[:：]\s*([^\n]{4,80})",
        r"公司名称\s*[:：]\s*([^\n]{4,80})",
    ):
        m = re.search(pat, t)
        if m:
            name = _clean_company_candidate(m.group(1))
            if name:
                return to_simplified(name)

    # 2) 编制单位
    m = re.search(r"编制单位[:：]\s*([^\n]{2,60})", t)
    if m:
        name = _clean_company_candidate(m.group(1))
        if name:
            return to_simplified(name)

    # 3) 封面优先：仅看前 800 字，取最早出现的「…股份有限公司」
    head = t[:800]
    head_hits = list(_COMPANY_RE.finditer(head))
    if head_hits:
        share = [h for h in head_hits if "股份有限公司" in h.group(1)]
        pick = (share or head_hits)[0].group(1)
        name = _clean_company_candidate(pick)
        if name:
            return to_simplified(name)

    # 4) 全文兜底：跳过释义表行，优先含「股份」且更早出现
    best: tuple[int, int, str] | None = None  # (is_share_penalty, index, name)
    for line in t.splitlines()[:200]:
        if _GLOSSARY_LINE_RE.search(line):
            continue
        if "指" in line and ("有限公司" in line or "股份" in line):
            # 「简称 指 全称」释义，跳过
            continue
        for m in _COMPANY_RE.finditer(line):
            cand = _clean_company_candidate(m.group(1))
            if not cand or len(cand) < 4:
                continue
            idx = t.find(cand)
            if idx < 0:
                idx = 10_000
            key = (0 if "股份" in cand else 1, idx, cand)
            if best is None or key < best:
                best = key
    if best:
        return to_simplified(best[2])
    return None


def _clean_company_candidate(raw: str) -> str | None:
    name = (raw or "").strip()
    name = re.split(r"\s{2,}|单位|股票|证券|代码|简称", name)[0].strip()
    name = name.strip("：:·•-—|｜/\\")
    # 去掉常见前缀噪声
    name = re.sub(r"^(公司的|本公司|本集团)+", "", name)
    if len(name) < 4:
        return None
    if not re.search(r"(公司|集团|集團)$", name):
        # 允许「…股份有限公司」中间截断已由正则保证后缀
        if "公司" not in name and "集团" not in name and "集團" not in name:
            return None
    return name


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
