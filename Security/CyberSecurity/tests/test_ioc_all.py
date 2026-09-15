"""Consolidated IOC gate: extractor / validate / scoring / mitre / schemas /
fallback / CSV-safety / XSS / tenant dedupe. Run: pytest tests/test_ioc_all.py -v"""

import csv
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ioc import __version__  # noqa: E402
from backend.app.ioc.dedupe import dedupe_key  # noqa: E402
from backend.app.ioc.export import export_csv, html_escape, safe_csv_cell  # noqa: E402
from backend.app.ioc.extractor import (  # noqa: E402
    extract_all,
    extract_ips,
    extract_urls,
    refang_text,
)
from backend.app.ioc.mitre_map import MITRE_VERSION, map_ioc  # noqa: E402
from backend.app.ioc.pipeline import analyze  # noqa: E402
from backend.app.ioc.schemas import AnalyzeResponse, IOCAnalyzeRequest  # noqa: E402
from backend.app.ioc.scoring import score_ioc  # noqa: E402
from backend.app.ioc.validate import (  # noqa: E402
    is_allowlisted,
    is_valid_domain,
    is_valid_hash,
    is_valid_ip,
)

TID = "00000000-0000-0000-0000-000000000001"
CID = "00000000-0000-0000-0000-000000000002"
EID = "00000000-0000-0000-0000-000000000003"


def _req(text=None, **kw):
    return IOCAnalyzeRequest(
        tenant_id=kw.get("tenant_id", TID),
        case_id=kw.get("case_id", CID),
        evidence_id=kw.get("evidence_id", EID),
        text=text,
        source_type=kw.get("source_type", "generic"),
    )


# --- 1. extractor defang ----------------------------------------------------
class TestExtractorDefang:
    def test_hxxp_brackets(self):
        assert refang_text("hxxp://evil[.]example[.]com/login") == "http://evil.example.com/login"

    def test_hxxps_parens_colon(self):
        assert refang_text("hxxps[:]//secure(.)example(.)tk") == "https://secure.example.tk"

    def test_ip_defang_extract(self):
        hits = extract_ips("Failed login from 10[.]0[.]0[.]1")
        assert any(h["raw"] == "10[.]0[.]0[.]1" for h in hits), hits

    def test_url_defang_extract(self):
        hits = extract_urls("see hxxp://evil[.]tk/login for details")
        assert len(hits) == 1 and hits[0]["type"] == "url"

    def test_dot_word_and_all(self):
        assert "evil.example.com" in refang_text("evil[dot]example[dot]com")
        hits = extract_all("Failed login from 10[.]0[.]0[.]1 via hxxp://evil[.]tk/login")
        types = {h["type"] for h in hits}
        assert {"ip", "url"} <= types


# --- 2. validate rejects version-numbers / UUIDs / 48-hex -------------------
class TestValidate:
    def test_reject_version_numbers(self):
        for v in ("1.2.3", "v2.4.1", "10.0.0"):
            assert not is_valid_domain(v), v

    def test_reject_uuid(self):
        u = "123e4567-e89b-12d3-a456-426614174000"
        assert not is_valid_domain(u)
        assert not is_valid_hash(u)

    def test_reject_48_hex(self):
        h48 = "ab" * 24
        assert len(h48) == 48
        assert not is_valid_hash(h48)

    def test_accept_real(self):
        assert is_valid_domain("evil.tk")
        assert is_valid_ip("203.0.113.10")
        assert is_valid_hash("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        assert not is_valid_hash("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")  # empty-file

    def test_pipeline_drops_version_noise(self):
        resp = analyze(_req("software version 1.2.3 released, see http://evil.tk/login"))
        vals = [r.value_normalized for r in resp.iocs]
        assert not any(v in ("1.2.3",) for v in vals)
        assert any("evil.tk" in v for v in vals)


# --- 3. scoring: private-cap + phishing critical ----------------------------
class TestScoring:
    def test_private_cap(self):
        score, level, reasons = score_ioc("ip", "192.168.1.5", "failed ssh brute force")
        assert score <= 10, (score, reasons)
        assert "private-ip-cap:10" in reasons

    def test_phishing_critical(self):
        score, level, reasons = score_ioc(
            "url", "http://evil.tk/login.exe", "verify paypal account clicked downloaded"
        )
        assert level == "CRITICAL" and score >= 80, (score, level, reasons)
        assert any(r.startswith("phishing-keyword") for r in reasons)

    def test_public_ip_not_capped(self):
        score, _, reasons = score_ioc("ip", "203.0.113.10", "failed ssh brute force")
        assert score > 10 and "private-ip-cap:10" not in reasons

    def test_allowlisted_capped(self):
        assert is_allowlisted("127.0.0.1")


# --- 4. mitre mapping: 4 rules ----------------------------------------------
class TestMitre:
    def test_rule1_phishing(self):
        res = map_ioc("url", "http://evil.tk/login", "verify account")
        assert any(r["id"] == "T1566.002" for r in res)

    def test_rule2_bruteforce(self):
        res = map_ioc("ip", "203.0.113.10", "multiple failed ssh logins")
        assert any(r["id"] == "T1110" for r in res)

    def test_rule3_user_exec(self):
        res = map_ioc("hash", "d41d8cd98f00b204e9800998ecf8427e", "dropped payload.exe executed")
        assert any(r["id"] == "T1204" for r in res)

    def test_rule4_c2(self):
        res = map_ioc("domain", "beacon.example.com", "dns beacon c2 channel over http")
        assert any(r["id"] == "T1071.001" for r in res)

    def test_version_pin_and_cap(self):
        assert MITRE_VERSION == "v19.2-2025-10-24"
        assert len(map_ioc("url", "http://x.tk/login", "phish dns beacon .exe fail")) <= 3


# --- 5. schemas: null-text allowed ------------------------------------------
class TestSchemas:
    def test_null_text_allowed(self):
        req = IOCAnalyzeRequest(tenant_id=TID, case_id=CID, evidence_id=EID, text=None)
        assert req.text is None
        assert req.options.enable_fallback is True

    def test_contract_frozen_fields(self):
        schema = json.loads((ROOT / "contracts" / "ioc.schema.json").read_text())
        assert set(schema["x-frozen-fields"]) == {
            "tenant_id", "evidence_id", "type", "value", "value_normalized",
            "raw_found", "context_snippet", "description", "raw_text",
            "dedupe_key", "risk_score", "risk_level", "confidence",
            "mitre_ids", "tags", "source", "status", "fallback_used",
            "first_seen", "last_seen",
        }
        assert schema["additionalProperties"] is False


# --- 6. fallback flag --------------------------------------------------------
class TestFallback:
    def test_none_input_fallback(self):
        resp = analyze(_req(None))
        assert resp.iocs == [] and resp.fallback_used is True

    def test_response_carries_flag(self):
        resp = AnalyzeResponse(
            analysis_id=EID, tenant_id=TID, case_id=CID, evidence_id=EID,
            source_type="generic", fallback_used=True, text_bytes=0,
        )
        assert resp.fallback_used is True

    def test_empty_extract_no_crash(self):
        assert extract_all("") == [] and extract_all(None) == []


# --- 7. CSV injection safe export -------------------------------------------
class TestCsvSafe:
    def test_no_cell_starts_with_dangerous(self):
        payloads = ["=cmd|'/c calc'!A0", "+1+1", "-2-3", "@evil.com", "|evil", "%x", "\t=HYPERLINK(1)"]
        rows = [{"v": p} for p in payloads]
        out = export_csv(rows, ["v"])
        cells = [r["v"] for r in csv.DictReader(io.StringIO(out))]
        assert all(not c.startswith(("=", "+", "-", "@")) for c in cells), cells

    def test_safe_cell_prefix(self):
        assert safe_csv_cell("=1+1").startswith("'")
        assert safe_csv_cell("normal") == "normal"
        assert safe_csv_cell(None) == ""


# --- 8. XSS escape -----------------------------------------------------------
class TestXss:
    def test_escape(self):
        x = html_escape('<script>alert("xss")</script>')
        assert "<script>" not in x and "&lt;script&gt;" in x

    def test_quotes_escaped(self):
        assert "&quot;" in html_escape('"q"') and "&#x27;" in html_escape("'q'")


# --- 9. tenant dedupe_key determinism ---------------------------------------
class TestDedupe:
    def test_deterministic(self):
        k1 = dedupe_key(TID, "domain", "Evil.TK.")
        k2 = dedupe_key(TID, "domain", "evil.tk")
        assert k1 == k2 and len(k1) == 64

    def test_tenant_scoped(self):
        assert dedupe_key(TID, "domain", "evil.tk") != dedupe_key(CID, "domain", "evil.tk")

    def test_type_scoped(self):
        assert dedupe_key(TID, "url", "evil.tk") != dedupe_key(TID, "domain", "evil.tk")

    def test_pipeline_dedupes_repeats(self):
        resp = analyze(_req("http://evil.tk/login and http://evil.tk/login"))
        keys = [r.dedupe_key for r in resp.iocs if "evil.tk" in r.value_normalized]
        assert len(keys) >= 1 and len(set(keys)) == 1


def test_version_present():
    assert __version__ == "1.0.0"
