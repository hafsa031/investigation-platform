"""Sprint-2 integration tests: forensic adapter + sender + e2e (offline)."""
from __future__ import annotations

import uuid


def _engine_result():
    """Hand-built dict mirroring the REAL process_evidence() keys (verified in
    team repo Forensic/forensic_engine.py: hash, file_identification,
    filesystem_metadata, exif, document_metadata, log_entries, timeline_events)."""
    return {
        "evidence_id": "e1", "case_id": "c1",
        "hash": {"algorithm": "SHA-256", "hash_value": "ab" * 32},
        "file_identification": {"declared_extension": "log", "detected_extension": "log",
                                "mime_type": "text/plain", "category": "log", "is_mismatch": False},
        "filesystem_metadata": {"file_name": "auth.log", "size_bytes": 10},
        "exif": {"has_exif": False}, "document_metadata": None,
        "log_entries": [
            {"line_number": 1, "timestamp": "2026-10-12T08:01:11", "level": None,
             "source_ip": "198.51.100.23", "raw_line": "Failed password for root from 198.51.100.23"},
            {"line_number": 2, "timestamp": "2026-10-12T08:01:14", "level": None,
             "source_ip": "198.51.100.23", "raw_line": "Failed password for root from 198.51.100.23"},
            {"line_number": 3, "timestamp": "2026-10-12T08:01:19", "level": None,
             "source_ip": "198.51.100.23", "raw_line": "Failed password for admin from 198.51.100.23"},
        ],
        "timeline_events": [], "processing_errors": [],
    }


def test_adapter_text_and_classify():
    from backend.app.ioc import forensic_adapter as FA
    res = _engine_result()
    text = FA.evidence_text(res)
    assert "198.51.100.23" in text and len(text.encode()) <= 5_242_880
    out = FA.forensic_inputs(res, "e1")
    assert out[0]["severity"] == "suspicious" and "3 failed-auth" in out[0]["title"]
    assert out[0]["timestamp"] == "2026-10-12T08:01:11"


def test_adapter_mismatch_and_normal():
    from backend.app.ioc import forensic_adapter as FA
    res = _engine_result()
    res["file_identification"]["is_mismatch"] = True
    res["log_entries"] = []
    assert FA.forensic_inputs(res, "e1")[0]["severity"] == "suspicious"
    res["file_identification"]["is_mismatch"] = False
    assert FA.forensic_inputs(res, "e1")[0]["severity"] == "normal"


def test_sender_fail_open():
    import os
    from backend.app.ioc import sender as S
    os.environ["BACKEND_URL"] = "http://127.0.0.1:9"  # nothing listens: must fail open
    out = S.send_case_results(str(uuid.uuid4()), [{"ioc": "x"}], [{"type": "ip"}])
    assert out["findings"]["sent"] is False and out["iocs"]["sent"] is False
    assert "reason" in out["findings"]


def test_e2e_case_runs():
    import subprocess
    p = subprocess.run(["python3", "scripts/e2e_case.py"], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    assert "CASE SUMMARY" in p.stdout and '"verdict"' in p.stdout
