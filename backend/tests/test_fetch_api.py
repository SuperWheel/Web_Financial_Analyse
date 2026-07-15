"""年报在线拉取 API 测试（httpx mock，不依赖外网）。"""
from __future__ import annotations

from unittest.mock import patch

from app.services.fetching.http_util import FetchError


def test_cninfo_securities_mocked(client):
    fake = [
        {
            "code": "603486",
            "name": "科沃斯",
            "org_id": "GD134549",
            "category": "A股",
            "type": "shj",
            "column": "sse",
        }
    ]
    with patch(
        "app.services.fetching.service.search_cninfo_securities",
        return_value=fake,
    ):
        r = client.get(
            "/api/imports/fetch/cninfo/securities",
            params={"q": "科沃斯机器人股份有限公司"},
        )
    assert r.status_code == 200, r.text
    assert r.json()[0]["code"] == "603486"


def test_cninfo_search_by_name_param_q(client):
    fake = [
        {
            "source": "cninfo",
            "code": "600519",
            "name": "贵州茅台",
            "org_id": "x",
            "year": 2024,
            "title": "2024年年度报告",
            "announce_date": "2025-01-01",
            "announcement_id": "1",
            "adjunct_url": "a.PDF",
            "pdf_url": "https://static.cninfo.com.cn/a.PDF",
        }
    ]
    with patch(
        "app.services.fetching.service.search_cninfo_annual",
        return_value=fake,
    ) as m:
        r = client.get(
            "/api/imports/fetch/cninfo/search",
            params={"q": "贵州茅台", "year": 2024},
        )
    assert r.status_code == 200
    m.assert_called_once()
    assert m.call_args[0][0] == "贵州茅台"
    assert r.json()[0]["code"] == "600519"

def test_cninfo_search_mocked(client):
    fake = [
        {
            "source": "cninfo",
            "code": "603486",
            "name": "科沃斯",
            "org_id": "GD134549",
            "year": 2024,
            "title": "2024年年度报告",
            "announce_date": "2025-04-26",
            "announcement_id": "1",
            "adjunct_url": "finalpage/x.PDF",
            "pdf_url": "https://static.cninfo.com.cn/finalpage/x.PDF",
        }
    ]
    with patch(
        "app.services.fetching.service.search_cninfo_annual",
        return_value=fake,
    ):
        r = client.get(
            "/api/imports/fetch/cninfo/search",
            params={"code": "603486", "year": 2024},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["title"] == "2024年年度报告"
    assert body[0]["pdf_url"].startswith("https://")


def test_cninfo_search_error(client):
    with patch(
        "app.services.fetching.service.search_cninfo_annual",
        side_effect=FetchError("巨潮未找到证券：xxx"),
    ):
        r = client.get(
            "/api/imports/fetch/cninfo/search",
            params={"code": "xxx", "year": 2024},
        )
    assert r.status_code == 400
    assert "未找到" in r.json()["detail"]


def test_fetch_from_url_mocked(client):
    pdf = b"%PDF-1.4 fake content for test"

    def fake_download(url, **kwargs):
        assert url.startswith("https://")
        return pdf, "report.pdf"

    with patch(
        "app.services.fetching.service.download_pdf_bytes",
        side_effect=fake_download,
    ), patch(
        "app.services.import_service.run_pipeline_on_path"
    ) as pipe:
        # 最小 pipeline 结果
        from types import SimpleNamespace

        pipe.return_value = SimpleNamespace(
            company_hint="测试公司",
            company_code_hint="000001",
            report_year=2024,
            period_type="annual",
            quarter=None,
            accounting_standard="CAS",
            unit_scale=1.0,
            scope="consolidated",
            confidence=0.9,
            fill_mode="REVIEW_REQUIRED",
            raw_extract={},
            coverage={},
            issues=[],
            unmapped=[],
            status="ok",
            error_message=None,
            to_draft_dict=lambda: {
                "statements": {"balance": {"total_assets": 1.0}},
                "report_year": 2024,
                "period_type": "annual",
            },
        )
        r = client.post(
            "/api/imports/fetch/from-url",
            json={"url": "https://example.com/a.pdf"},
        )
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["source_type"] == "pdf_url"
    assert job["status"] in ("review", "failed", "mapped")
    assert job["report_year"] == 2024


def test_cninfo_download_mocked(client):
    pdf = b"%PDF-1.4 cninfo"

    with patch(
        "app.services.fetching.service.download_pdf_bytes",
        return_value=(pdf, "x.pdf"),
    ), patch(
        "app.services.import_service.run_pipeline_on_path"
    ) as pipe:
        from types import SimpleNamespace

        pipe.return_value = SimpleNamespace(
            company_hint=None,
            company_code_hint=None,
            report_year=None,
            period_type="annual",
            quarter=None,
            accounting_standard=None,
            unit_scale=None,
            scope=None,
            confidence=0.5,
            fill_mode="REVIEW_REQUIRED",
            raw_extract={},
            coverage={},
            issues=[],
            unmapped=[],
            status="ok",
            error_message=None,
            to_draft_dict=lambda: {"statements": {}},
        )
        r = client.post(
            "/api/imports/fetch/cninfo/download",
            json={
                "pdf_url": "https://static.cninfo.com.cn/finalpage/x.PDF",
                "code": "603486",
                "title": "2024年年度报告",
                "year": 2024,
                "name": "科沃斯",
            },
        )
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["source_type"] == "pdf_cninfo"
    # 预填回退
    assert job["company_code_hint"] == "603486"
    assert job["report_year"] == 2024


def test_fetch_rejects_non_http(client):
    r = client.post(
        "/api/imports/fetch/from-url",
        json={"url": "file:///etc/passwd"},
    )
    assert r.status_code == 400
