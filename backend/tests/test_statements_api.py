"""三大报表 CRUD 接口测试。"""
from __future__ import annotations


def _create_company(client, name: str = "示例科技") -> int:
    resp = client.post("/api/companies", json={"name": name, "code": f"C-{name}"})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_balance_sheet_annual(client):
    cid = _create_company(client)
    resp = client.post(
        f"/api/companies/{cid}/balance-sheets",
        json={
            "year": 2024,
            "period_type": "annual",
            "quarter": None,
            "monetary_funds": 1000.5,
            "total_assets": 5000,
            "total_liabilities": 2000,
            "total_equity": 3000,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["company_id"] == cid
    assert body["year"] == 2024
    assert body["period_type"] == "annual"
    assert body["quarter"] is None
    assert float(body["monetary_funds"]) == 1000.5
    assert float(body["total_assets"]) == 5000


def test_create_balance_sheet_quarterly(client):
    cid = _create_company(client)
    resp = client.post(
        f"/api/companies/{cid}/balance-sheets",
        json={"year": 2024, "period_type": "quarterly", "quarter": 1, "total_assets": 1},
    )
    assert resp.status_code == 201
    assert resp.json()["quarter"] == 1


def test_period_validation_annual_with_quarter(client):
    cid = _create_company(client)
    resp = client.post(
        f"/api/companies/{cid}/balance-sheets",
        json={"year": 2024, "period_type": "annual", "quarter": 1},
    )
    assert resp.status_code == 422


def test_period_validation_quarterly_without_quarter(client):
    cid = _create_company(client)
    resp = client.post(
        f"/api/companies/{cid}/balance-sheets",
        json={"year": 2024, "period_type": "quarterly"},
    )
    assert resp.status_code == 422


def test_period_conflict_annual(client):
    cid = _create_company(client)
    path = f"/api/companies/{cid}/balance-sheets"
    assert client.post(path, json={"year": 2024, "period_type": "annual"}).status_code == 201
    resp = client.post(path, json={"year": 2024, "period_type": "annual"})
    assert resp.status_code == 409


def test_list_and_filter(client):
    cid = _create_company(client)
    path = f"/api/companies/{cid}/balance-sheets"
    client.post(path, json={"year": 2023, "period_type": "annual"})
    client.post(path, json={"year": 2024, "period_type": "annual"})
    client.post(path, json={"year": 2024, "period_type": "quarterly", "quarter": 2})

    all_rows = client.get(path)
    assert all_rows.status_code == 200
    assert len(all_rows.json()) == 3

    y2024 = client.get(path, params={"year": 2024})
    assert len(y2024.json()) == 2

    annual = client.get(path, params={"period_type": "annual"})
    assert len(annual.json()) == 2


def test_get_update_delete_balance_sheet(client):
    cid = _create_company(client)
    created = client.post(
        f"/api/companies/{cid}/balance-sheets",
        json={"year": 2024, "period_type": "annual", "total_assets": 10},
    ).json()
    sid = created["id"]

    got = client.get(f"/api/companies/{cid}/balance-sheets/{sid}")
    assert got.status_code == 200
    assert float(got.json()["total_assets"]) == 10

    patched = client.patch(
        f"/api/companies/{cid}/balance-sheets/{sid}",
        json={"total_assets": 99.5, "total_equity": 40},
    )
    assert patched.status_code == 200
    assert float(patched.json()["total_assets"]) == 99.5
    assert float(patched.json()["total_equity"]) == 40

    deleted = client.delete(f"/api/companies/{cid}/balance-sheets/{sid}")
    assert deleted.status_code == 204
    assert client.get(f"/api/companies/{cid}/balance-sheets/{sid}").status_code == 404


def test_company_not_found(client):
    resp = client.get("/api/companies/999/balance-sheets")
    assert resp.status_code == 404


def test_statement_wrong_company(client):
    c1 = _create_company(client, "甲")
    c2 = _create_company(client, "乙")
    sid = client.post(
        f"/api/companies/{c1}/balance-sheets",
        json={"year": 2024, "period_type": "annual"},
    ).json()["id"]
    resp = client.get(f"/api/companies/{c2}/balance-sheets/{sid}")
    assert resp.status_code == 404


def test_income_statement_crud(client):
    cid = _create_company(client)
    path = f"/api/companies/{cid}/income-statements"
    created = client.post(
        path,
        json={
            "year": 2024,
            "period_type": "annual",
            "operating_revenue": 10000,
            "net_profit": 1200,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert float(body["operating_revenue"]) == 10000
    assert float(body["net_profit"]) == 1200

    listed = client.get(path)
    assert len(listed.json()) == 1

    sid = body["id"]
    client.patch(f"{path}/{sid}", json={"net_profit": 1500})
    assert float(client.get(f"{path}/{sid}").json()["net_profit"]) == 1500
    assert client.delete(f"{path}/{sid}").status_code == 204


def test_cash_flow_statement_crud(client):
    cid = _create_company(client)
    path = f"/api/companies/{cid}/cash-flow-statements"
    created = client.post(
        path,
        json={
            "year": 2024,
            "period_type": "quarterly",
            "quarter": 3,
            "net_cash_flow_operating": 500,
            "net_increase_in_cash": 80,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["quarter"] == 3
    assert float(body["net_cash_flow_operating"]) == 500

    # 同季冲突
    conflict = client.post(
        path,
        json={"year": 2024, "period_type": "quarterly", "quarter": 3},
    )
    assert conflict.status_code == 409

    assert client.delete(f"{path}/{body['id']}").status_code == 204
