"""财务比率 API 与计算口径测试。"""
from __future__ import annotations


def _create_company(client, name: str = "比率测试公司") -> int:
    r = client.post("/api/companies", json={"name": name, "code": "RATIO1"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_statements(client, cid: int) -> None:
    bs = {
        "year": 2025,
        "period_type": "annual",
        "monetary_funds": 100.0,
        "inventories": 20.0,
        "total_current_assets": 200.0,
        "total_current_liabilities": 100.0,
        "total_assets": 500.0,
        "total_liabilities": 200.0,
        "total_equity": 300.0,
        "total_equity_parent": 280.0,
    }
    inc = {
        "year": 2025,
        "period_type": "annual",
        "operating_revenue": 1000.0,
        "operating_cost": 600.0,
        "operating_profit": 200.0,
        "net_profit": 120.0,
        "net_profit_parent": 110.0,
    }
    cf = {
        "year": 2025,
        "period_type": "annual",
        "net_cash_flow_operating": 150.0,
    }
    assert client.post(f"/api/companies/{cid}/balance-sheets", json=bs).status_code == 201
    assert client.post(f"/api/companies/{cid}/income-statements", json=inc).status_code == 201
    assert (
        client.post(f"/api/companies/{cid}/cash-flow-statements", json=cf).status_code == 201
    )


def test_ratios_snapshot_and_periods(client):
    cid = _create_company(client)
    _seed_statements(client, cid)

    periods = client.get(f"/api/companies/{cid}/ratio-periods")
    assert periods.status_code == 200
    body = periods.json()
    assert len(body) == 1
    assert body[0]["year"] == 2025
    assert body[0]["has_balance"] is True
    assert body[0]["has_income"] is True

    snap = client.get(
        f"/api/companies/{cid}/ratios",
        params={"year": 2025, "period_type": "annual"},
    )
    assert snap.status_code == 200, snap.text
    data = snap.json()
    assert data["summary"]["available"] >= 10
    by_key = {r["key"]: r for r in data["ratios"]}

    assert by_key["current_ratio"]["value"] == 2.0
    assert by_key["quick_ratio"]["value"] == 1.8
    assert by_key["cash_ratio"]["value"] == 1.0
    assert abs(by_key["debt_to_asset"]["value"] - 0.4) < 1e-6
    assert abs(by_key["gross_margin"]["value"] - 0.4) < 1e-6
    assert abs(by_key["net_margin"]["value"] - 0.12) < 1e-6
    # 优先归母口径
    assert by_key["roe"]["variant"] == "net_profit_parent / total_equity_parent"
    assert abs(by_key["roe"]["value"] - (110.0 / 280.0)) < 1e-6
    assert abs(by_key["ocfr"]["value"] - 0.15) < 1e-6


def test_ratios_zero_denominator(client):
    cid = _create_company(client, name="零分母公司")
    client.post(
        f"/api/companies/{cid}/balance-sheets",
        json={
            "year": 2024,
            "period_type": "annual",
            "total_current_assets": 10.0,
            "total_current_liabilities": 0.0,
            "total_assets": 10.0,
            "total_liabilities": 0.0,
            "total_equity": 10.0,
        },
    )
    snap = client.get(
        f"/api/companies/{cid}/ratios",
        params={"year": 2024, "period_type": "annual"},
    )
    assert snap.status_code == 200
    by_key = {r["key"]: r for r in snap.json()["ratios"]}
    assert by_key["current_ratio"]["value"] is None
    assert by_key["current_ratio"]["reason"] == "zero_denominator"


def test_ratio_history(client):
    cid = _create_company(client, name="历史公司")
    _seed_statements(client, cid)
    # 第二年部分数据
    client.post(
        f"/api/companies/{cid}/balance-sheets",
        json={
            "year": 2024,
            "period_type": "annual",
            "total_current_assets": 100.0,
            "total_current_liabilities": 50.0,
            "total_assets": 200.0,
            "total_liabilities": 80.0,
            "total_equity": 120.0,
            "monetary_funds": 40.0,
            "inventories": 10.0,
        },
    )
    client.post(
        f"/api/companies/{cid}/income-statements",
        json={
            "year": 2024,
            "period_type": "annual",
            "operating_revenue": 500.0,
            "operating_cost": 300.0,
            "net_profit": 50.0,
        },
    )
    hist = client.get(
        f"/api/companies/{cid}/ratios/history",
        params={"period_type": "annual", "keys": "current_ratio,roe"},
    )
    assert hist.status_code == 200, hist.text
    data = hist.json()
    assert "current_ratio" in data["series"]
    assert len(data["series"]["current_ratio"]["points"]) == 2


def test_ratios_company_404(client):
    r = client.get(
        "/api/companies/99999/ratios",
        params={"year": 2025, "period_type": "annual"},
    )
    assert r.status_code == 404
