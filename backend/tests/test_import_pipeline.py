"""公开年报导入管道测试（科沃斯 CAS PDF + API）。"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KEWO_PDF = ROOT / "年报参考" / "ashare-cas" / "603486_科沃斯_2025年报.pdf"
YINGSHI_PDF = ROOT / "年报参考" / "ashare-cas" / "688775_影石创新_2025年报.pdf"


@pytest.mark.skipif(not KEWO_PDF.exists(), reason="缺少科沃斯年报 PDF fixture")
def test_pipeline_ecovacs_core_fields():
    from app.services.importing.pipeline import run_pipeline_on_path

    result = run_pipeline_on_path(KEWO_PDF)
    assert result.status == "mapped", result.error_message
    assert result.report_year == 2025
    assert result.unit_scale == 1.0
    bs = result.statements.get("balance") or {}
    inc = result.statements.get("income") or {}
    cf = result.statements.get("cashflow") or {}
    # 核心字段存在
    assert "monetary_funds" in bs
    assert "total_assets" in bs or "total_liabilities" in bs
    assert "operating_revenue" in inc
    assert "net_profit" in inc
    assert "net_cash_flow_operating" in cf
    # 金额量级：科沃斯营收约 190 亿
    assert inc["operating_revenue"] > 1e10
    assert bs["monetary_funds"] > 1e9
    # v1 权益别名热修 + 常见 v2
    assert "paid_in_capital" in bs or "capital_reserve" in bs
    assert "retained_earnings" in bs or "surplus_reserve" in bs
    assert result.disclosure_lines, "应产出 L0 披露行"
    assert any(d.get("mapped_to") for d in result.disclosure_lines)


def test_rollup_rule_exact_match():
    from app.core.rollup_rules import match_rollup
    from app.services.importing.text_utils import normalize_label

    rule = match_rollup("balance", normalize_label("衍生金融资产"))
    assert rule is not None
    assert rule["mapped_to"] == "trading_financial_assets"


@pytest.mark.skipif(not YINGSHI_PDF.exists(), reason="缺少影石年报 PDF fixture")
def test_pipeline_insta360_finds_statements():
    from app.services.importing.pipeline import run_pipeline_on_path

    result = run_pipeline_on_path(YINGSHI_PDF)
    assert result.status == "mapped", result.error_message
    assert result.statements.get("balance")
    assert result.statements.get("income")


def test_import_api_upload_and_commit(client, tmp_path):
    """无真实 PDF 时用最小失败文件测 API 契约；有科沃斯则完整入库。"""
    if KEWO_PDF.exists():
        content = KEWO_PDF.read_bytes()
        filename = "科沃斯2025年报.pdf"
    else:
        content = b"%PDF-1.4 fake"
        filename = "fake.pdf"

    resp = client.post(
        "/api/imports/filings",
        files={"file": (filename, content, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    job = resp.json()
    assert "id" in job
    assert job["status"] in {"review", "failed", "mapped"}

    detail = client.get(f"/api/imports/filings/{job['id']}")
    assert detail.status_code == 200

    if job["status"] in {"review", "mapped"} and (job.get("draft") or {}).get("statements"):
        # 确保年份
        if not job.get("report_year"):
            client.patch(
                f"/api/imports/filings/{job['id']}",
                json={"report_year": 2025, "period_type": "annual"},
            )
        committed = client.post(
            f"/api/imports/filings/{job['id']}/commit",
            json={"overwrite": True},
        )
        assert committed.status_code == 200, committed.text
        body = committed.json()
        assert body["status"] == "committed"
        assert body["company_id"]
        assert body.get("commit_result", {}).get("statement_ids")
        # L0 双写
        assert body.get("commit_result", {}).get("disclosure_lines_written", 0) > 0


def test_import_rejects_non_pdf(client):
    resp = client.post(
        "/api/imports/filings",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
