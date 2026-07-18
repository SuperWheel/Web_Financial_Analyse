"""东财公开接口：补全 A 股行业（best-effort，失败返回 None）。"""
from __future__ import annotations

import re
from typing import Any

import httpx

from app.services.fetching.http_util import DEFAULT_UA, _throttle

EM_STOCK_GET = "https://push2.eastmoney.com/api/qt/stock/get"
# f57=代码 f58=名称 f127=所属行业（板块）
EM_FIELDS = "f57,f58,f127"
_CODE_RE = re.compile(r"^\d{6}$")


def _secids_for_code(code: str) -> list[str]:
    """按代码猜测市场：6/9→沪 1.；0/3→深 0.；其余都试。"""
    c = code.strip()
    if c.startswith(("6", "9")):
        return [f"1.{c}", f"0.{c}"]
    if c.startswith(("0", "3")):
        return [f"0.{c}", f"1.{c}"]
    return [f"1.{c}", f"0.{c}"]


def fetch_industry(
    code: str, *, client: httpx.Client | None = None
) -> str | None:
    """返回行业名（如「小家电」「白酒Ⅱ」）；失败 None，不抛。"""
    c = (code or "").strip()
    if not _CODE_RE.match(c):
        return None

    own = client is None
    http = client or httpx.Client(
        timeout=12.0,
        headers={
            "User-Agent": DEFAULT_UA,
            "Referer": "https://finance.eastmoney.com/",
        },
        follow_redirects=True,
    )
    try:
        for secid in _secids_for_code(c):
            try:
                _throttle()
                r = http.get(
                    EM_STOCK_GET,
                    params={"secid": secid, "fields": EM_FIELDS},
                )
                if r.status_code >= 400:
                    continue
                data: Any = r.json().get("data")
                if not isinstance(data, dict):
                    continue
                ind = data.get("f127")
                if ind is None:
                    continue
                s = str(ind).strip()
                if s and s not in ("-", "None", "null"):
                    return s
            except Exception:  # noqa: BLE001
                continue
        return None
    finally:
        if own:
            http.close()
