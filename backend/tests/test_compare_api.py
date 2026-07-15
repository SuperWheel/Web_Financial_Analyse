"""多期科目对比 API 测试。"""
from __future__ import annotations


def _create_company(client, name: str = "对比测试公司", code: str = "CMP1") -> int:
    r = client.post("/api/companies", json={"name": name, "code": code})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_two_years(client, cid: int) -> None:
    for year, assets, cash, rev, cost, ocf in (
        (2024, 500.0, 100.0, 1000.0, 600.0, 150.0),
        (2025, 600.0, 150.0, 1200.0, 700.0, 180.0),
    ):
        assert (
            client.post(
                f"/api/companies/{cid}/balance-sheets",
                json={
                    "year": year,
                    "period_type": "annual",
                    "monetary_funds": cash,
                    "total_assets": assets,
                    "total_liabilities": assets * 0.4,
                    "total_equity": assets * 0.6,
                    "total_current_assets": cash + 50,
                },
            ).status_code
            == 201
        )
        assert (
            client.post(
                f"/api/companies/{cid}/income-statements",
                json={
                    "year": year,
                    "period_type": "annual",
                    "operating_revenue": rev,
                    "operating_cost": cost,
                    "net_profit": rev - cost - 100,
                },
            ).status_code
            == 201
        )
        assert (
            client.post(
                f"/api/companies/{cid}/cash-flow-statements",
                json={
                    "year": year,
                    "period_type": "annual",
                    "net_cash_flow_operating": ocf,
                },
            ).status_code
            == 201
        )


def test_compare_periods_and_balance_matrix(client):
    cid = _create_company(client)
    _seed_two_years(client, cid)

    periods = client.get(f"/api/companies/{cid}/compare-periods")
    assert periods.status_code == 200
    body = periods.json()
    assert len(body) == 2
    assert body[0]["year"] == 2025  # 新→旧
    assert body[0]["has_balance"] is True

    resp = client.get(
        f"/api/companies/{cid}/compare",
        params={"statement_type": "balance", "period_type": "annual"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["company_id"] == cid
    assert data["statement_type"] == "balance"
    assert data["base_field"] == "total_assets"
    assert [p["year"] for p in data["periods"]] == [2024, 2025]  # 升序

    by_key = {
        row["key"]: row for g in data["groups"] for row in g["rows"]
    }
    cash = by_key["monetary_funds"]
    assert cash["values"] == [100.0, 150.0]
    assert cash["deltas"][0] is None
    assert cash["deltas"][1] == 50.0
    assert abs(cash["delta_pcts"][1] - 0.5) < 1e-9
    # 结构：100/500=0.2，150/600=0.25
    assert abs(cash["structure_pcts"][0] - 0.2) < 1e-9
    assert abs(cash["structure_pcts"][1] - 0.25) < 1e-9

    assets = by_key["total_assets"]
    assert assets["values"] == [500.0, 600.0]
    assert assets["deltas"][1] == 100.0


def test_compare_income_and_years_filter(client):
    cid = _create_company(client, name="利润对比", code="CMP2")
    _seed_two_years(client, cid)

    resp = client.get(
        f"/api/companies/{cid}/compare",
        params={
            "statement_type": "income",
            "period_type": "annual",
            "years": "2025",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["periods"]) == 1
    assert data["periods"][0]["year"] == 2025
    assert data["base_field"] == "operating_revenue"

    by_key = {row["key"]: row for g in data["groups"] for row in g["rows"]}
    rev = by_key["operating_revenue"]
    assert rev["values"] == [1200.0]
    assert rev["deltas"] == [None]
    assert abs(rev["structure_pcts"][0] - 1.0) < 1e-9


def test_compare_cashflow_no_structure(client):
    cid = _create_company(client, name="现金流对比", code="CMP3")
    _seed_two_years(client, cid)

    resp = client.get(
        f"/api/companies/{cid}/compare",
        params={"statement_type": "cashflow", "period_type": "annual"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["base_field"] is None
    by_key = {row["key"]: row for g in data["groups"] for row in g["rows"]}
    ocf = by_key["net_cash_flow_operating"]
    assert ocf["values"] == [150.0, 180.0]
    assert ocf["deltas"][1] == 30.0
    assert ocf["structure_pcts"] == [None, None]


def test_compare_missing_company(client):
    r = client.get(
        "/api/companies/99999/compare",
        params={"statement_type": "balance"},
    )
    assert r.status_code == 404


def test_compare_invalid_statement_type(client):
    cid = _create_company(client, name="非法类型", code="CMP4")
    r = client.get(
        f"/api/companies/{cid}/compare",
        params={"statement_type": "unknown"},
    )
    assert r.status_code == 422


def test_compare_zero_prev_delta_pct_null(client):
    cid = _create_company(client, name="零基期", code="CMP5")
    for year, cash in ((2024, 0.0), (2025, 10.0)):
        assert (
            client.post(
                f"/api/companies/{cid}/balance-sheets",
                json={
                    "year": year,
                    "period_type": "annual",
                    "monetary_funds": cash,
                    "total_assets": 100.0,
                },
            ).status_code
            == 201
        )
    resp = client.get(
        f"/api/companies/{cid}/compare",
        params={"statement_type": "balance", "period_type": "annual"},
    )
    assert resp.status_code == 200
    by_key = {
        row["key"]: row for g in resp.json()["groups"] for row in g["rows"]
    }
    cash = by_key["monetary_funds"]
    assert cash["deltas"][1] == 10.0
    assert cash["delta_pcts"][1] is None  # prev=0
