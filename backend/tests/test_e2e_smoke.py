"""最小端到端烟测：创建企业 → 录入三表 → 比率/对比可读。

不依赖 PDF fixture，纯 API 路径，保证主链路在 CI 中始终可跑。
"""
from __future__ import annotations


def test_company_statements_ratios_compare_smoke(client):
    # 1) 创建企业
    r = client.post(
        "/api/companies",
        json={"name": "E2E 烟测公司", "code": "E2E001", "industry": "测试"},
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    # 2) 两期三表（便于对比/同比）
    for year, scale in ((2024, 1.0), (2025, 1.1)):
        bs = {
            "year": year,
            "period_type": "annual",
            "monetary_funds": 100.0 * scale,
            "inventories": 20.0 * scale,
            "total_current_assets": 200.0 * scale,
            "total_current_liabilities": 100.0 * scale,
            "total_assets": 500.0 * scale,
            "total_liabilities": 200.0 * scale,
            "total_equity": 300.0 * scale,
            "total_equity_parent": 280.0 * scale,
        }
        inc = {
            "year": year,
            "period_type": "annual",
            "operating_revenue": 1000.0 * scale,
            "operating_cost": 600.0 * scale,
            "operating_profit": 200.0 * scale,
            "net_profit": 120.0 * scale,
            "net_profit_parent": 110.0 * scale,
        }
        cf = {
            "year": year,
            "period_type": "annual",
            "net_cash_flow_operating": 150.0 * scale,
        }
        assert (
            client.post(f"/api/companies/{cid}/balance-sheets", json=bs).status_code == 201
        ), year
        assert (
            client.post(f"/api/companies/{cid}/income-statements", json=inc).status_code
            == 201
        ), year
        assert (
            client.post(f"/api/companies/{cid}/cash-flow-statements", json=cf).status_code
            == 201
        ), year

    # 3) 列表可读
    listed = client.get(f"/api/companies/{cid}/balance-sheets")
    assert listed.status_code == 200
    assert len(listed.json()) >= 2

    # 4) 比率快照 + 历史
    periods = client.get(f"/api/companies/{cid}/ratio-periods")
    assert periods.status_code == 200
    assert len(periods.json()) >= 2

    snap = client.get(
        f"/api/companies/{cid}/ratios",
        params={"year": 2025, "period_type": "annual"},
    )
    assert snap.status_code == 200, snap.text
    body = snap.json()
    assert body["summary"]["available"] >= 8
    by_key = {r["key"]: r for r in body["ratios"]}
    assert by_key["current_ratio"]["value"] == 2.0
    assert abs(by_key["gross_margin"]["value"] - 0.4) < 1e-6

    hist = client.get(
        f"/api/companies/{cid}/ratios/history",
        params={"period_type": "annual"},
    )
    assert hist.status_code == 200, hist.text
    series = hist.json()["series"]
    assert "current_ratio" in series
    assert len(series["current_ratio"]["points"]) >= 2

    # 5) 多期对比矩阵
    cmp_periods = client.get(f"/api/companies/{cid}/compare-periods")
    assert cmp_periods.status_code == 200, cmp_periods.text
    assert len(cmp_periods.json()) >= 2

    matrix = client.get(
        f"/api/companies/{cid}/compare",
        params={
            "statement_type": "balance",
            "period_type": "annual",
            "years": "2024,2025",
        },
    )
    assert matrix.status_code == 200, matrix.text
    m = matrix.json()
    assert len(m.get("periods") or []) >= 2
    assert m.get("groups"), "compare matrix should include field groups"
