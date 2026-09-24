"""Sprint-2 tests: Threat Findings + correlation + case endpoints (all offline)."""
from __future__ import annotations

import uuid

from backend.app.ioc import correlation as C
from backend.app.ioc import threat_findings as TF
from backend.app.ioc.pipeline import analyze
from backend.app.ioc.schemas import IOCAnalyzeRequest


def _req(text, source_type="generic", case=None, ev=None):
    return IOCAnalyzeRequest(
        tenant_id=uuid.uuid4(), case_id=case or uuid.uuid4(),
        evidence_id=ev or uuid.uuid4(), text=text, source_type=source_type)  # type: ignore[arg-type]


def test_findings_shape_and_severity():
    r = analyze(_req("Failed password for root from 198.51.100.23 failed failed", "auth_log"))
    assert r.findings, "every analysis must emit findings"
    f = [x for x in r.findings if x["ioc"] == "198.51.100.23"][0]
    assert set(f) >= {"ioc", "type", "source", "severity", "timestamp", "reason"}
    assert f["severity"] in ("high", "critical")  # heuristic HIGH maps up
    assert f["source"]["line_no"] >= 1 and "T1110" in (f.get("mitre_ids") or [])


def test_severity_never_from_ai_alone():
    from backend.app.ioc.schemas import IOCRecord
    rec = IOCRecord(type="ip", value_normalized="8.8.8.8", raw_found="8.8.8.8",
                    risk_score=20, risk_level="low", reasons=["base"],
                    mitre_ids=[], dedupe_key="k")
    assert TF.severity_for(rec) == "low"  # no AI -> base severity stands


def test_correlation_shared_and_timeline_and_rollup():
    ev1, ev2, case = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    text = "see 198.51.100.23 and http://evil.example.com/x"
    a1 = analyze(_req(text, "auth_log", case, ev1))
    a2 = analyze(_req(text, "auth_log", case, ev2))
    recs = list(a1.iocs) + list(a2.iocs)
    shared = C.shared_iocs(recs)
    assert any(s["evidence_count"] >= 2 for s in shared)  # pivot detected
    tl = C.timeline(recs)
    assert [t["line_no"] or 0 for t in tl] == sorted(t["line_no"] or 0 for t in tl)
    roll = C.case_rollup(recs, [{"evidence_id": str(ev1), "severity": "suspicious"}])
    assert roll["ioc_count"] == len(recs) and roll["verdict"] in ("normal", "suspicious", "critical")


def test_case_endpoints():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.app.ioc.api import router, _ANALYSES
    _ANALYSES.clear()
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    case = str(uuid.uuid4())
    for txt in ("Failed password from 198.51.100.23 failed", "phishing login at http://evil.example.com/login"):
        r = c.post("/api/v1/iocs/analyze", json={
            "tenant_id": str(uuid.uuid4()), "case_id": case, "evidence_id": str(uuid.uuid4()),
            "text": txt, "source_type": "auth_log"})
        assert r.status_code == 201
    iocs = c.get(f"/api/v1/iocs/by-case/{case}/iocs")
    assert iocs.status_code == 200 and iocs.json()["total"] >= 2
    fnd = c.get(f"/api/v1/iocs/by-case/{case}/findings", params={"severity": "high"})
    assert fnd.status_code == 200
    summ = c.get(f"/api/v1/iocs/by-case/{case}/summary")
    assert summ.status_code == 200 and summ.json()["evidence_count"] == 2
    assert summ.json()["verdict"] in ("normal", "suspicious", "critical")
