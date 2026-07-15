"""企业（Company）CRUD 接口测试。"""
from __future__ import annotations


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_company_success(client):
    resp = client.post(
        "/api/companies",
        json={"name": "示例科技", "code": "EX001", "industry": "信息技术"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "示例科技"
    assert body["code"] == "EX001"


def test_create_company_name_required(client):
    resp = client.post("/api/companies", json={"code": "EX002"})
    assert resp.status_code == 422  # 校验失败


def test_create_company_name_blank(client):
    resp = client.post("/api/companies", json={"name": "   "})
    assert resp.status_code == 422


def test_create_company_code_conflict(client):
    client.post("/api/companies", json={"name": "甲公司", "code": "DUP"})
    resp = client.post("/api/companies", json={"name": "乙公司", "code": "DUP"})
    assert resp.status_code == 409


def test_list_companies(client):
    client.post("/api/companies", json={"name": "甲"})
    client.post("/api/companies", json={"name": "乙"})
    resp = client.get("/api/companies")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_company_not_found(client):
    resp = client.get("/api/companies/999")
    assert resp.status_code == 404


def test_update_company(client):
    create = client.post("/api/companies", json={"name": "旧名"}).json()
    resp = client.patch(f"/api/companies/{create['id']}", json={"industry": "制造业"})
    assert resp.status_code == 200
    assert resp.json()["industry"] == "制造业"


def test_delete_company(client):
    create = client.post("/api/companies", json={"name": "待删"}).json()
    resp = client.delete(f"/api/companies/{create['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/companies/{create['id']}").status_code == 404
