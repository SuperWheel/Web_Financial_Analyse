"""巨潮资讯 A 股年报检索（公开披露接口，礼貌限速）。"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from app.services.fetching.http_util import (
    DEFAULT_UA,
    FetchError,
    _throttle,
    new_client,
)

TOP_SEARCH = "https://www.cninfo.com.cn/new/information/topSearch/query"
HIS_QUERY = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC_PDF = "https://static.cninfo.com.cn/"
REFERER = (
    "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch"
    "?url=disclosure/list/search"
)

_EXCLUDE_TITLE = re.compile(
    r"(摘要|取消|英文|English|半年度|一季度|三季度|季度报告|已取消)",
    re.I,
)
_ANNUAL_TITLE = re.compile(r"年度报告|年报")
_CODE_RE = re.compile(r"^\d{6}$")
# 公司全称常见后缀：巨潮 topSearch 对过长全称常无结果，需回退简称
_NAME_SUFFIXES = (
    "股份有限公司",
    "有限责任公司",
    "有限公司",
    "集团股份",
    "集团公司",
    "集团",
    "控股",
    "公司",
)


def _column_for_type(stock_type: str | None, code: str) -> str:
    t = (stock_type or "").lower()
    if t.startswith("sz") or code.startswith(("0", "1", "2", "3")):
        # 深市常见 000/001/002/003/300
        if code.startswith(("0", "1", "2", "3")) and not code.startswith("6"):
            return "szse"
    if t.startswith("bj") or code.startswith(("8", "4")):
        return "bj"
    if t.startswith("sh") or code.startswith("6"):
        return "sse"
    # type 字段如 shj / szj
    if "sz" in t:
        return "szse"
    if "bj" in t:
        return "bj"
    return "sse"


def _name_query_variants(key: str) -> list[str]:
    """生成名称检索变体：原串 + 去后缀简称 + 逐步缩短。"""
    key = key.strip()
    if not key:
        return []
    if _CODE_RE.match(key):
        return [key]
    variants: list[str] = [key]
    # 去空白
    compact = re.sub(r"\s+", "", key)
    if compact != key:
        variants.append(compact)
    # 逐级剥后缀
    cur = compact
    changed = True
    while changed:
        changed = False
        for suf in _NAME_SUFFIXES:
            if cur.endswith(suf) and len(cur) > len(suf) + 1:
                cur = cur[: -len(suf)]
                if cur and cur not in variants:
                    variants.append(cur)
                changed = True
                break
    # 巨潮对「xx机器人」等中间名常无结果：再从右缩短到 ≥2 字（最多 5 档）
    base = variants[-1]
    extra = 0
    for length in range(len(base) - 1, 1, -1):
        if extra >= 5:
            break
        cand = base[:length]
        if cand and cand not in variants:
            variants.append(cand)
            extra += 1
    return variants


def _item_to_stock(item: dict[str, Any]) -> dict[str, Any] | None:
    code = str(item.get("code") or "").strip()
    org_id = str(item.get("orgId") or "").strip()
    if not code or not org_id:
        return None
    name = str(item.get("zwjc") or item.get("name") or code)
    return {
        "code": code,
        "org_id": org_id,
        "name": name,
        "category": item.get("category"),
        "type": item.get("type"),
        "column": _column_for_type(str(item.get("type") or ""), code),
    }


def _rank_stock(item: dict[str, Any], key: str) -> tuple:
    """排序：精确代码 > 精确简称 > 名称包含 > A股优先。"""
    code = str(item.get("code") or "")
    name = str(item.get("zwjc") or item.get("name") or "")
    cat = str(item.get("category") or "")
    key_c = key.strip()
    exact_code = 0 if code == key_c else 1
    exact_name = 0 if name == key_c else 1
    contains = 0 if (key_c in name or name in key_c) else 1
    a_share = 0 if "A" in cat or cat == "A股" else 1
    return (exact_code, exact_name, contains, a_share, code)


def _top_search_raw(key: str, client: httpx.Client) -> list[dict[str, Any]]:
    _throttle()
    r = client.post(
        TOP_SEARCH,
        data={"keyWord": key, "maxNum": "20"},
        headers={
            "User-Agent": DEFAULT_UA,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": REFERER,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    if r.status_code >= 400:
        raise FetchError(f"巨潮证券检索失败 HTTP {r.status_code}")
    arr = r.json()
    if not isinstance(arr, list):
        return []
    return [x for x in arr if isinstance(x, dict)]


def search_securities(
    query: str, *, client: httpx.Client | None = None
) -> list[dict[str, Any]]:
    """按代码或公司名称检索证券列表（去重）。"""
    key = (query or "").strip()
    if not key:
        raise FetchError("证券代码/名称不能为空")

    own = client is None
    c = client or new_client()
    try:
        seen: dict[str, dict[str, Any]] = {}
        last_err: str | None = None
        for variant in _name_query_variants(key):
            try:
                arr = _top_search_raw(variant, c)
            except FetchError as exc:
                last_err = str(exc.detail if hasattr(exc, "detail") else exc)
                continue
            # 按与查询的相关度排序后并入
            arr_sorted = sorted(arr, key=lambda it: _rank_stock(it, variant))
            for item in arr_sorted:
                stock = _item_to_stock(item)
                if stock is None:
                    continue
                # 同代码保留第一次（更高相关）
                if stock["code"] not in seen:
                    seen[stock["code"]] = stock
            if seen:
                break
        if not seen:
            msg = f"巨潮未找到证券：{key}"
            if last_err:
                msg = f"{msg}（{last_err}）"
            raise FetchError(msg)
        # 最终按原查询再排一次
        return sorted(seen.values(), key=lambda s: _rank_stock(
            {"code": s["code"], "zwjc": s["name"], "category": s.get("category")},
            key,
        ))
    finally:
        if own:
            c.close()


def resolve_stock(
    code_or_name: str, *, client: httpx.Client | None = None
) -> dict[str, Any]:
    """解析唯一/最优证券；名称支持全称回退简称。"""
    stocks = search_securities(code_or_name, client=client)
    return stocks[0]


def _ms_to_date(ms: Any) -> str | None:
    try:
        v = int(ms)
        if v > 1e12:
            v = v / 1000.0
        return datetime.fromtimestamp(v).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def _is_annual_full_report(title: str) -> bool:
    t = title or ""
    if not _ANNUAL_TITLE.search(t):
        return False
    if _EXCLUDE_TITLE.search(t):
        return False
    return True


def search_annual_reports(
    code_or_name: str,
    year: int,
    *,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """检索指定年份年度报告（全文，非摘要）。"""
    if year < 1990 or year > 2100:
        raise FetchError("年份无效")

    own = client is None
    c = client or new_client()
    try:
        stock = resolve_stock(code_or_name, client=c)
        se_date = f"{year}-01-01~{year + 1}-12-31"
        form = {
            "pageNum": "1",
            "pageSize": "50",
            "column": stock["column"],
            "tabName": "fulltext",
            "plate": "",
            "stock": f"{stock['code']},{stock['org_id']}",
            "searchkey": "",
            "secid": "",
            "category": "category_ndbg_szsh;",
            "trade": "",
            "seDate": se_date,
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        _throttle()
        r = c.post(
            HIS_QUERY,
            data=form,
            headers={
                "User-Agent": DEFAULT_UA,
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.cninfo.com.cn",
                "Referer": REFERER,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        if r.status_code >= 400:
            raise FetchError(f"巨潮公告检索失败 HTTP {r.status_code}")
        payload = r.json()
        anns = payload.get("announcements") or []
        out: list[dict[str, Any]] = []
        for a in anns:
            title = str(a.get("announcementTitle") or "")
            # 去 HTML 高亮
            title_clean = re.sub(r"<[^>]+>", "", title)
            if not _is_annual_full_report(title_clean):
                continue
            adjunct = a.get("adjunctUrl") or ""
            if not adjunct:
                continue
            # 标题年份过滤：优先标题含目标年
            if str(year) not in title_clean and str(year - 1) not in title_clean:
                # seDate 已限制；仍保留（有些标题不写年）
                pass
            if str(year) not in title_clean:
                # 严格：标题须含报告年度
                continue
            pdf_url = adjunct if str(adjunct).startswith("http") else STATIC_PDF + str(adjunct).lstrip("/")
            out.append(
                {
                    "source": "cninfo",
                    "code": stock["code"],
                    "name": stock["name"],
                    "org_id": stock["org_id"],
                    "year": year,
                    "title": title_clean,
                    "announce_date": _ms_to_date(a.get("announcementTime")),
                    "announcement_id": str(a.get("announcementId") or a.get("id") or ""),
                    "adjunct_url": str(adjunct),
                    "pdf_url": pdf_url,
                }
            )
        return out
    finally:
        if own:
            c.close()
