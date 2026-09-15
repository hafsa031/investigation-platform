"""Per-file expectations for the synthetic test-data pack (all offline)."""
from __future__ import annotations

import uuid
from pathlib import Path

TD = Path(__file__).parent.parent / "backend" / "app" / "ioc" / "tests" / "fixtures" / "testdata"


def _analyze(fname: str, source_type: str = "generic"):
    from backend.app.ioc.pipeline import analyze
    from backend.app.ioc.schemas import IOCAnalyzeRequest
    text = (TD / fname).read_text()
    return analyze(IOCAnalyzeRequest(
        tenant_id=uuid.uuid4(), case_id=uuid.uuid4(), evidence_id=uuid.uuid4(),
        text=text, source_type=source_type))  # type: ignore[arg-type]


def test_auth_bruteforce():
    r = _analyze("auth_ssh_bruteforce.log", "auth_log")
    by_val = {i.value_normalized: i for i in r.iocs}
    assert "198.51.100.23" in by_val
    assert by_val["198.51.100.23"].risk_level in ("high", "critical")
    assert "T1110" in by_val["198.51.100.23"].mitre_ids
    if "127.0.0.1" in by_val:
        assert by_val["127.0.0.1"].risk_score <= 10


def test_firewall_c2():
    r = _analyze("firewall_c2_beacon.log", "firewall")
    by_val = {i.value_normalized: i for i in r.iocs}
    assert "203.0.113.55" in by_val
    assert not any(i.value_normalized == "cdn.example" and i.risk_level in ("high", "critical") for i in r.iocs)


def test_phish():
    r = _analyze("phish_credential_harvest.eml", "email_header")
    urls = [i for i in r.iocs if i.type == "url"]
    assert any("acme-portal-secure.net" in u.value_normalized for u in urls)
    assert any("T1566.002" in u.mitre_ids for u in urls)
    assert any("evil-example.tk" in i.value_normalized for i in r.iocs)


def test_malware_hashes():
    r = _analyze("malware_drop_report.txt", "file_text")
    types = {i.type for i in r.iocs}
    assert {"sha256", "md5", "sha1"} <= types
    assert not any(len(i.value_normalized) == 48 for i in r.iocs)
    assert "d41d8cd98f00b204e9800998ecf8427e" not in {i.value_normalized for i in r.iocs}
    assert any("T1204" in i.mitre_ids for i in r.iocs)


def test_benign_precision():
    r = _analyze("benign_ham.eml", "email_header")
    assert not any(i.risk_level in ("high", "critical") for i in r.iocs), \
        [(i.value_normalized, i.risk_level) for i in r.iocs]


def test_defang_variants():
    r = _analyze("defang_variants.txt")
    vals = {i.value_normalized for i in r.iocs}
    assert "http://bad-one.example.com/payment" in vals
    assert "198.51.100.23" in vals
    assert any("evil-example.tk" in v for v in vals)


def test_edge_noise():
    r = _analyze("edge_noise.txt")
    assert not any(i.risk_level in ("high", "critical") for i in r.iocs), \
        [(i.value_normalized, i.risk_level) for i in r.iocs]
    vals = {i.value_normalized for i in r.iocs}
    assert "550e8400-e29b-41d4-a716-446655440000" not in vals
    assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" not in vals
    assert "999.999.999.999" not in vals


def test_metadata_strings():
    r = _analyze("metadata_strings.txt", "file_text")
    vals = {i.value_normalized for i in r.iocs}
    assert "files.evil-example.tk" in vals
    assert "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" in vals
    assert "bounce@evil-example.tk" in vals
