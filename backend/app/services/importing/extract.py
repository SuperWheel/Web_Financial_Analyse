"""表格/行文本抽取。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pdfplumber

from app.services.importing.locate import Segment
from app.services.importing.text_utils import (
    extract_amounts,
    parse_amount,
    to_simplified,
)

_NOTE_RE = re.compile(
    r"^(七|八|九|十|十一|十二|十三|十四|十五|十六|十七|十八|十九)?[、.．]?\d+([、.．-]\d+)?$"
)


@dataclass
class RawRow:
    label: str
    amounts: list[float]
    page: int
    source: str  # grid / line


@dataclass
class ExtractedTable:
    kind: str
    rows: list[RawRow] = field(default_factory=list)
    channel: str = "grid"
    header_years: list[int] = field(default_factory=list)


def _is_header_row(cells: list[str]) -> bool:
    joined = "".join(cells)
    return any(
        k in joined for k in ("项目", "項 目", "附注", "附註", "年度", "月", "日", "期末", "期初")
    )


def _cell_amounts(cell: str) -> list[float]:
    cell = (cell or "").strip()
    if not cell:
        return []
    if _NOTE_RE.fullmatch(cell):
        return []
    # 无千分位/小数的短编号
    if not re.search(r"\d{1,3}(,\d{3})+", cell) and not re.search(r"\d+\.\d{2}", cell):
        if re.fullmatch(r"[A-Za-z0-9IVX一二三四五六七八九十、.．-]+", cell) and not re.search(
            r"\d{5,}", cell
        ):
            return []
    amts = extract_amounts(cell)
    if amts:
        return amts
    pa = parse_amount(cell)
    return [pa] if pa is not None else []


def extract_grid(pdf_path: str, seg: Segment) -> ExtractedTable:
    rows: list[RawRow] = []
    years: list[int] = []
    with pdfplumber.open(pdf_path) as doc:
        last = min(seg.end_page, len(doc.pages) - 1)
        for pi in range(seg.start_page, last + 1):
            page = doc.pages[pi]
            text = to_simplified(page.extract_text() or "")
            years += [int(y) for y in re.findall(r"(20\d{2})", text[:500])]
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                for raw in table:
                    cells = [(c or "").replace("\n", "").strip() for c in raw]
                    if not any(cells):
                        continue
                    if _is_header_row(cells):
                        years += [int(y) for y in re.findall(r"(20\d{2})", "".join(cells))]
                        continue
                    label = cells[0]
                    if not label or label in {"项目", "項 目"}:
                        continue
                    amounts: list[float] = []
                    for cell in cells[1:]:
                        amounts.extend(_cell_amounts(cell))
                    rows.append(
                        RawRow(label=label, amounts=amounts, page=pi + 1, source="grid")
                    )
    uniq_years = sorted({y for y in years if 1990 <= y <= 2100}, reverse=True)
    return ExtractedTable(kind=seg.kind, rows=rows, channel="grid", header_years=uniq_years)


def extract_lines(pdf_path: str, seg: Segment) -> ExtractedTable:
    rows: list[RawRow] = []
    years: list[int] = []
    with pdfplumber.open(pdf_path) as doc:
        last = min(seg.end_page, len(doc.pages) - 1)
        for pi in range(seg.start_page, last + 1):
            text = to_simplified(doc.pages[pi].extract_text() or "")
            years += [int(y) for y in re.findall(r"(20\d{2})", text[:500])]
            for line in text.splitlines():
                line = line.strip()
                if len(line) < 2:
                    continue
                amts = extract_amounts(line)
                if not amts:
                    if line.endswith("：") or line.endswith(":"):
                        rows.append(
                            RawRow(label=line, amounts=[], page=pi + 1, source="line")
                        )
                    continue
                label = line
                m = re.search(
                    r"[（(]?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*[)）]?", line
                )
                if m:
                    label = line[: m.start()].strip()
                label = re.sub(r"\s+", "", label)
                # 去掉尾部附注「七、1」
                label = re.sub(r"(七|八|九|十)?[、.]\d+$", "", label)
                if not label or len(label) > 40:
                    continue
                if "有限公司" in label and len(amts) <= 1:
                    continue
                rows.append(RawRow(label=label, amounts=amts, page=pi + 1, source="line"))
    uniq_years = sorted({y for y in years if 1990 <= y <= 2100}, reverse=True)
    return ExtractedTable(kind=seg.kind, rows=rows, channel="line", header_years=uniq_years)


def choose_channel(grid: ExtractedTable, lines: ExtractedTable) -> ExtractedTable:
    def score(t: ExtractedTable) -> tuple[int, int]:
        with_amt = sum(1 for r in t.rows if r.amounts)
        return (with_amt, len(t.rows))

    if score(grid)[0] >= 12:
        return grid
    if score(lines)[0] >= 12:
        return lines
    return grid if score(grid) >= score(lines) else lines


def extract_segment(pdf_path: str, seg: Segment) -> ExtractedTable:
    g = extract_grid(pdf_path, seg)
    if sum(1 for r in g.rows if r.amounts) < 12:
        b = extract_lines(pdf_path, seg)
        return choose_channel(g, b)
    return g
