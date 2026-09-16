"""Full end-to-end verification for Intern-5 IOC module (Sprint-1 demo path)."""
from __future__ import annotations
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.ioc.schemas import IOCAnalyzeRequest
from backend.app.ioc.pipeline import analyze
from backend.app.ioc.api import router
from backend.app.ioc.export import safe_csv_cell, export_csv, html_escape
from backend.app.ioc.dedupe import dedupe_key
from backend.app.ioc import __version__

FIX = Path(__file__).parent.parent / "backend" / "app" / "ioc" / "tests" / "fixtures"


def _req(text, source_type="generic"):
    return IOCAnalyzeRequest(
        tenant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4(),
        text=text, source_type=source_type,
    )


def test_e2e_version():
    assert __version__ == "1.0.0"


def test_e2e_auth_log():
    text = (FIX / "auth.log").read_text()
    r = analyze(_req(text, "auth_log"))
    vals = {i.value_normalized for i in r.iocs}
    assert "198.51.100.23" in vals  # attacker IP found
    assert not any(i.value_normalized == "127.0.0.1" and i.risk_level in ("high", "critical") for i in r.iocs)
    assert any("T1110" in i.mitre_ids for i in r.iocs)  # bruteforce mapped
    assert all(i.line_no and i.line_no >= 1 for i in r.iocs)
    assert all(len(i.context_snippet) <= 400 for i in r.iocs)


def test_e2e_phish_eml():
    text = (FIX / "phish.eml").read_text()
    r = analyze(_req(text, "email_header"))
    urls = [i for i in r.iocs if i.type == "url"]
    assert urls, "phishing URL must extract"
    assert any("acme-portal-secure.net" in u.value_normalized for u in urls)
    assert any("T1566.002" in u.mitre_ids for u in urls)
    assert any(u.risk_level in ("medium", "high", "critical") for u in urls)
    assert any("acme-portal-secure" in u.raw_found or "acme-portal-secure" in u.value_normalized for u in urls)


def test_e2e_doc_hashes():
    text = (FIX / "doc_with_hashes.txt").read_text()
    r = analyze(_req(text, "file_text"))
    types = {i.type for i in r.iocs}
    assert "sha256" in types and "md5" in types
    assert not any(len(i.value_normalized) == 48 for i in r.iocs)  # 48-char invalid dropped


def test_e2e_api_full_path():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    assert c.get("/api/v1/iocs/health").status_code == 200
    tid, cid, eid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    resp = c.post("/api/v1/iocs/analyze", json={
        "tenant_id": tid, "case_id": cid, "evidence_id": eid,
        "text": "Failed password from 198.51.100.23, visit hxxp://acme-portal-secure[.]net/login",
        "source_type": "auth_log"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["fallback_used"] is False and len(body["iocs"]) >= 2
    lst = c.get("/api/v1/iocs/", params={"page": 1, "page_size": 50})
    assert lst.status_code == 200 and lst.json()["total"] >= 1
    bad = c.get("/api/v1/iocs/", params={"page": 1, "page_size": 201})
    assert bad.status_code == 422


def test_e2e_fallback_and_5mb_cap():
    from backend.app.ioc.schemas import IOCAnalyzeOptions
    eid = uuid.uuid4()
    r = analyze(IOCAnalyzeRequest(tenant_id=uuid.uuid4(), case_id=uuid.uuid4(),
                evidence_id=eid, text=None, source_type="generic"))
    assert r.fallback_used is True and r.iocs == []
    # truncation via small max_bytes (fast, no 6MB extract)
    big = ("benign line no ioc here\n" * 300) + "evil 8.8.8.8\n"
    req = IOCAnalyzeRequest(tenant_id=uuid.uuid4(), case_id=uuid.uuid4(),
            evidence_id=uuid.uuid4(), text=big, source_type="generic",
            options=IOCAnalyzeOptions(max_bytes=1000, context_window=40))
    r2 = analyze(req)
    assert r2.text_truncated is True and r2.text_bytes <= 1000


def test_e2e_dedupe_tenant_isolation_and_security():
    tid, other = uuid.uuid4(), uuid.uuid4()
    eid = uuid.uuid4()
    assert dedupe_key(str(tid), "domain", "Evil.TK.") == dedupe_key(str(tid), "domain", "evil.tk")
    assert dedupe_key(str(tid), "ip", "1.2.3.4") != dedupe_key(str(other), "ip", "1.2.3.4")
    assert dedupe_key(str(tid), "ip", "1.2.3.4") != dedupe_key(str(tid), "domain", "1.2.3.4")
    # pipeline evidence-scoped dedupe: repeats collapse to one record
    r = analyze(IOCAnalyzeRequest(tenant_id=tid, case_id=uuid.uuid4(), evidence_id=eid,
                text="8.8.8.8 and 8.8.8.8 again", source_type="generic"))
    assert len([i for i in r.iocs if i.value_normalized == "8.8.8.8"]) == 1
    # CSV injection
    # CSV injection: protective quote prefix, raw cell never starts with =+-@
    assert safe_csv_cell("=1+1").startswith("'") and not safe_csv_cell("=1+1").startswith(("=", "+", "-", "@"))
    csv_out = export_csv([{"v": "=HYPERLINK(1)"}], ["v"])
    assert "'=HYPERLINK" in csv_out
    # XSS
    assert "<script>" not in html_escape('<script>alert(1)</script>')
    # ReDoS timing guard (evil input fast)
    from backend.app.ioc.extractor import extract_all
    t0 = time.time()
    extract_all("a" * 5000 + "!" + "[" * 100)
    assert time.time() - t0 < 2.0
    # No secrets / no real victim data in fixtures
    blob = "".join((FIX / f).read_text() for f in ("auth.log", "phish.eml", "doc_with_hashes.txt"))
    assert "AKIA" not in blob and "8.8.4.4" not in blob
