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


def test_cninfo_batch_mixed_mocked(client):
    """多年批：ok / empty / error 混排，单年失败不中断。"""
    stock = {
        "code": "603486",
        "name": "科沃斯",
        "org_id": "x",
        "category": "A股",
        "type": "sz",
        "column": "szse",
    }
    cand_2023 = {
        "source": "cninfo",
        "code": "603486",
        "name": "科沃斯",
        "org_id": "x",
        "year": 2023,
        "title": "2023年年度报告",
        "announce_date": "2024-03-01",
        "announcement_id": "1",
        "adjunct_url": "a.PDF",
        "pdf_url": "https://static.cninfo.com.cn/a.PDF",
    }

    def fake_search(code, year):
        if year == 2022:
            return []
        if year == 2023:
            return [cand_2023]
        if year == 2024:
            raise FetchError("模拟检索失败")
        return []

    fake_job = type("J", (), {"id": 99})()

    with patch(
        "app.services.fetching.service.cninfo.search_securities",
        return_value=[stock],
    ), patch(
        "app.services.fetching.service.cninfo.search_annual_reports",
        side_effect=fake_search,
    ), patch(
        "app.services.fetching.service.create_job_from_cninfo_candidate",
        return_value=fake_job,
    ) as create_job:
        r = client.post(
            "/api/imports/fetch/cninfo/batch",
            json={
                "q": "603486",
                "years": [2024, 2022, 2023, 2023],
                "company_id": 1,
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == "603486"
    assert body["name"] == "科沃斯"
    assert body["years_requested"] == [2022, 2023, 2024]
    assert body["summary"] == {"ok": 1, "empty": 1, "error": 1}
    by_year = {row["year"]: row for row in body["results"]}
    assert by_year[2022]["status"] == "empty"
    assert by_year[2023]["status"] == "ok"
    assert by_year[2023]["job_id"] == 99
    assert by_year[2024]["status"] == "error"
    create_job.assert_called_once()
    kwargs = create_job.call_args.kwargs
    assert kwargs["year"] == 2023
    assert kwargs["company_id"] == 1


def test_cninfo_batch_rejects_empty_years(client):
    r = client.post(
        "/api/imports/fetch/cninfo/batch",
        json={"q": "603486", "years": []},
    )
    assert r.status_code == 422


def test_cninfo_batch_rejects_missing_q(client):
    r = client.post(
        "/api/imports/fetch/cninfo/batch",
        json={"years": [2023, 2024]},
    )
    assert r.status_code == 422


def test_cninfo_batch_too_many_years(client):
    years = list(range(2000, 2013))  # 13 years
    r = client.post(
        "/api/imports/fetch/cninfo/batch",
        json={"q": "603486", "years": years},
    )
    assert r.status_code == 422


def test_cninfo_search_years_multi_mocked(client):
    def fake_years(code, years):
        out = []
        for y in years:
            if y == 2022:
                continue
            out.append(
                {
                    "source": "cninfo",
                    "code": "603486",
                    "name": "科沃斯",
                    "org_id": "x",
                    "year": y,
                    "title": f"{y}年年度报告",
                    "announce_date": f"{y + 1}-03-01",
                    "announcement_id": str(y),
                    "adjunct_url": f"{y}.PDF",
                    "pdf_url": f"https://static.cninfo.com.cn/{y}.PDF",
                }
            )
        return out

    with patch(
        "app.services.fetching.service.search_cninfo_annual_years",
        side_effect=fake_years,
    ) as m:
        r = client.post(
            "/api/imports/fetch/cninfo/search-years",
            json={"q": "603486", "years": [2024, 2022, 2023]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert sorted(x["year"] for x in body) == [2023, 2024]
    m.assert_called_once()
    # years 原样传入 service（归一化在 service 内）
    assert m.call_args[0][0] == "603486"
    assert m.call_args[0][1] == [2024, 2022, 2023]


def test_cninfo_search_years_requires_q(client):
    r = client.post(
        "/api/imports/fetch/cninfo/search-years",
        json={"years": [2024]},
    )
    assert r.status_code == 422
