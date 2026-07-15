"""报表页区间定位：标题状态机。"""
from __future__ import annotations

from dataclasses import dataclass

import pdfplumber

from app.services.importing.text_utils import normalize_title, to_simplified


@dataclass
class Segment:
    kind: str  # balance / income / cashflow
    scope: str  # consolidated / parent / unknown
    start_page: int  # 0-based
    end_page: int  # inclusive 0-based
    title: str
    score: float


_TITLE_RULES: list[tuple[str, str, float, tuple[str, ...]]] = [
    ("balance", "consolidated", 1.0, ("合并资产负债表", "合併資產負債表")),
    ("balance", "parent", 0.7, ("母公司资产负债表",)),
    ("balance", "unknown", 0.55, ("资产负债表", "資產負債表", "财务状况表")),
    (
        "income",
        "consolidated",
        1.0,
        (
            "合并利润表",
            "合併利潤表",
            "合并利润表及",
            "合併經營狀況及全面",
            "合并经营状况及全面",
            "合併損益表",
            "合并损益表",
        ),
    ),
    ("income", "parent", 0.7, ("母公司利润表",)),
    ("income", "unknown", 0.55, ("利润表", "利潤表", "综合收益表", "收益表")),
    ("cashflow", "consolidated", 1.0, ("合并现金流量表", "合併現金流量表")),
    ("cashflow", "parent", 0.7, ("母公司现金流量表",)),
    ("cashflow", "unknown", 0.55, ("现金流量表", "現金流量表")),
]

_STOP_MARKERS = (
    "财务报表附注",
    "合併財務報表附註",
    "合并财务报表附注",
    "重要会计政策",
    "公司基本情况",
)


def _is_continuation_title(title: str) -> bool:
    """标题含「续」时视为同一张表的续页，不重置 start_page。"""
    t = normalize_title(title or "")
    return "续" in t or t.endswith("续") or "（续）" in (title or "") or "(续)" in (title or "")


def _classify_line(line: str) -> tuple[str, str, float] | None:
    raw = (line or "").strip()
    if not raw or len(raw) > 28 or len(raw) < 4:
        return None
    t = normalize_title(raw)
    if not t or len(t) < 4:
        return None
    if t[-1:].isdigit() and len(t) < 12:
        return None
    if any(
        x in t
        for x in (
            "抵销",
            "导致",
            "如下",
            "包括",
            "参见",
            "附注",
            "编制",
            "日后事项",
            "项目注释",
            "变动表",
        )
    ):
        return None
    best: tuple[str, str, float] | None = None
    for kind, scope, score, patterns in _TITLE_RULES:
        for p in patterns:
            pn = normalize_title(p)
            if not pn:
                continue
            hit = t == pn or t.startswith(pn)
            # 允许「合并资产负债表（续）」
            if not hit and pn in t and (
                len(t) <= len(pn) + 4 or _is_continuation_title(raw)
            ):
                hit = True
            if not hit:
                continue
            if scope != "parent" and "母公司" in t:
                continue
            cand = (kind, scope, score)
            if best is None or cand[2] > best[2]:
                best = cand
    return best


def locate_statements(pdf_path: str) -> list[Segment]:
    """扫描全文标题，返回各表合并优先区间。"""
    opens: dict[str, Segment] = {}
    closed: list[Segment] = []

    def close_kind(kind: str, end_page: int) -> None:
        seg = opens.pop(kind, None)
        if seg is None:
            return
        seg.end_page = max(seg.start_page, end_page)
        closed.append(seg)

    def close_all(end_page: int) -> None:
        for k in list(opens.keys()):
            close_kind(k, end_page)

    with pdfplumber.open(pdf_path) as doc:
        n = len(doc.pages)
        for i, page in enumerate(doc.pages):
            text = to_simplified(page.extract_text() or "")
            if any(normalize_title(m) in normalize_title(text[:800]) for m in _STOP_MARKERS):
                if i > 0 and opens:
                    close_all(i - 1)

            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                hit = _classify_line(line)
                if not hit:
                    continue
                kind, scope, score = hit
                existing_closed = [
                    s for s in closed if s.kind == kind and s.scope == "consolidated"
                ]
                if existing_closed and scope != "consolidated":
                    continue
                if kind in opens:
                    prev = opens[kind]
                    # 合并表已打开：忽略母公司/未知同名标题，避免截断合并区间
                    if prev.scope == "consolidated" and scope != "consolidated":
                        continue
                    if scope == "parent" and prev.scope == "consolidated":
                        continue
                    # 续页：保持原 start_page，只推进 end
                    if _is_continuation_title(line) and (
                        prev.scope == scope or prev.scope == "consolidated"
                    ):
                        prev.end_page = max(prev.end_page, i)
                        continue
                    # 同 kind 更高分 consolidated 可替换 parent/unknown
                    if scope == "consolidated" and prev.scope != "consolidated":
                        close_kind(kind, i - 1)
                    elif not _is_continuation_title(line):
                        close_kind(kind, i - 1)
                    else:
                        prev.end_page = max(prev.end_page, i)
                        continue
                # 已有 consolidated 关闭段时，不再开 parent/unknown
                if any(s.scope == "consolidated" for s in closed if s.kind == kind):
                    if scope != "consolidated":
                        continue
                opens[kind] = Segment(
                    kind=kind,
                    scope=scope,
                    start_page=i,
                    end_page=i,
                    title=line[:80],
                    score=score,
                )

        close_all(n - 1)

    best: dict[str, Segment] = {}
    for seg in closed:
        cur = best.get(seg.kind)

        def rank(s: Segment) -> tuple:
            # 合并优先、分高优先、更早的 start 优先（避免续页段覆盖表头）
            return (1 if s.scope == "consolidated" else 0, s.score, -s.start_page)

        if cur is None or rank(seg) > rank(cur):
            best[seg.kind] = seg

    ordered = sorted(best.values(), key=lambda s: s.start_page)
    for idx, seg in enumerate(ordered):
        if idx + 1 < len(ordered):
            # 扩展到下一张表之前，覆盖跨页
            seg.end_page = max(seg.end_page, ordered[idx + 1].start_page - 1)
        seg.end_page = max(seg.start_page, seg.end_page)

    return ordered
