"""共享 HTTP 下载：礼貌 UA、PDF 校验。"""
from __future__ import annotations

import time
from typing import Final
from urllib.parse import urlparse

import httpx

from app.services.exceptions import ServiceError

DEFAULT_UA = (
    "WebFinancialAnalyse/0.1 (+local research; respectful; contact: local)"
)
MAX_PDF_BYTES = 40 * 1024 * 1024
MIN_INTERVAL_SEC = 0.4

_last_request_at = 0.0


class FetchError(ServiceError):
    status_code = 400


def _throttle() -> None:
    global _last_request_at
    now = time.monotonic()
    wait = MIN_INTERVAL_SEC - (now - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def ensure_http_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        raise FetchError("URL 为空")
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("仅支持 http/https URL")
    if not parsed.netloc:
        raise FetchError("URL 无效")
    return u


def new_client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": DEFAULT_UA,
            "Accept": "*/*",
        },
    )


def download_pdf_bytes(
    url: str,
    *,
    client: httpx.Client | None = None,
    referer: str | None = None,
) -> tuple[bytes, str]:
    """下载并校验 PDF。返回 (content, filename_hint)。"""
    url = ensure_http_url(url)
    own = client is None
    c = client or new_client()
    try:
        _throttle()
        headers = {}
        if referer:
            headers["Referer"] = referer
        with c.stream("GET", url, headers=headers) as resp:
            if resp.status_code >= 400:
                raise FetchError(f"下载失败 HTTP {resp.status_code}：{url}")
            # 文件名
            name = urlparse(url).path.rsplit("/", 1)[-1] or "download.pdf"
            cd = resp.headers.get("content-disposition") or ""
            if "filename=" in cd:
                part = cd.split("filename=")[-1].strip().strip("\"'")
                if part:
                    name = part
            if not name.lower().endswith(".pdf"):
                name = f"{name}.pdf" if "." not in name else name

            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > MAX_PDF_BYTES:
                    raise FetchError("文件过大（>40MB）")
                chunks.append(chunk)
            content = b"".join(chunks)
    finally:
        if own:
            c.close()

    if not content:
        raise FetchError("下载内容为空")
    # PDF magic
    head = content[:5]
    if head != b"%PDF-" and b"%PDF" not in content[:1024]:
        ctype = ""
        raise FetchError("下载内容不是 PDF（缺少 %PDF 头）")
    return content, name
