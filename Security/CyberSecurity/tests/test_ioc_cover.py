"""Coverage-closing tests: normalize, validate, ai_enhance, extractor/scoring branches."""
from __future__ import annotations

from backend.app.ioc import normalize as N
from backend.app.ioc import validate as V
from backend.app.ioc import ai_enhance as AI
from backend.app.ioc import mitre_map as M
from backend.app.ioc.extractor import extract_all, refang_text
from backend.app.ioc.scoring import score_ioc


def test_normalize_all():
    assert N.normalize_ip(" 8.8.8.8 ") == "8.8.8.8"
    assert N.normalize_domain("Example.COM.") == "example.com"
    assert "xn--" in N.normalize_domain("münchen.de")
    assert N.normalize_url("HXXP://Evil.TK/Login").startswith("http://evil.tk")
    assert N.normalize_email("Admin@Example.COM") == "admin@example.com"
    assert N.normalize_hash("ABCDEF1234567890ABCDEF1234567890") == "abcdef1234567890abcdef1234567890"
    assert N.normalize(" Evil.TK. ", "domain") == "evil.tk"


def test_validate_all():
    assert V.is_valid_ip("8.8.8.8") and not V.is_valid_ip("999.1.1.1")
    assert V.is_valid_ip("2001:db8::1") and V.is_valid_ip("::1")
    assert V.is_valid_domain("evil.tk") and not V.is_valid_domain("localhost")
    assert not V.is_valid_domain("singlelabel") and not V.is_valid_domain("a.123")
    assert V.is_valid_email("u@evil.tk") and not V.is_valid_email("a@@evil.tk")
    assert not V.is_valid_email("user@localhost")
    assert V.is_valid_hash("5d41402abc4b2a76b9719d911017c592")
    assert not V.is_valid_hash("0" * 32)
    assert not V.is_valid_hash("d41d8cd98f00b204e9800998ecf8427e")  # empty-file
    assert not V.is_valid_hash("a" * 48)
    assert V.is_allowlisted("192.168.1.1", None) and V.is_allowlisted("127.0.0.1", None)
    assert V.is_allowlisted("example.com", None) and not V.is_allowlisted("evil.tk", None)
    out = V.resolve_overlaps([
        {"type": "domain", "raw": "evil.tk", "start": 7, "end": 14},
        {"type": "url", "raw": "http://evil.tk/login", "start": 0, "end": 19}])
    assert [o["type"] for o in out] == ["url"]


def _f(out):
    return out if isinstance(out, dict) else out.model_dump()


def test_ai_enhance_gating():
    assert AI.AI_RERANK_ENABLED is False
    r = [_f(o) for o in AI.rerank([{"ioc": "http://evil.tk/login"}], "phishing login page")]
    assert r[0]["delta"] == 0 and r[0]["accepted"] is False
    AI.AI_RERANK_ENABLED = True
    try:
        ok = [_f(o) for o in AI.rerank([{"ioc": "http://evil.tk/login", "delta": 5,
              "justification": "phishing login page shows credential theft attempt here",
              "technique_ids": ["T1566.002"], "confidence": 0.8}],
            "phishing login page shows credential theft attempt")]
        assert set(ok[0].keys()) >= {"delta", "accepted"} and -15 <= ok[0]["delta"] <= 15
        bad = [_f(o) for o in AI.rerank([{"ioc": "http://evil.tk/login",
              "justification": "mentions nothing grounded zzzqqqx",
              "technique_ids": ["T9999"], "confidence": 0.5}], "plain context here")]
        assert bad[0]["accepted"] is False or bad[0]["delta"] == 0
    finally:
        AI.AI_RERANK_ENABLED = False


def test_extractor_variants():
    assert any(c["type"] == "url" for c in extract_all("visit hxxps://bad[.]example[.]com/a"))
    assert any(c["type"] == "email" for c in extract_all("mail u[at]evil[.]tk now"))
    assert any(c["type"] == "sha1" for c in extract_all("sha1 da39a3ee5e6b4b0d3255bfef95601890afd80709 end"))
    assert any(c["type"] == "sha512" for c in extract_all("h " + "ab" * 64 + " end"))
    assert extract_all("") == [] and extract_all(None) == []
    assert "http" in refang_text("hxxp://a[.]b")


def test_scoring_branches():
    s, lvl, rs = score_ioc("domain", "xn--paypa1.com", "login verify here")
    assert s >= 40 and any("punycode" in r or "phishing" in r for r in rs)
    s2, _, r2 = score_ioc("url", "http://evil.com/payload.exe", "downloaded file")
    assert s2 >= 60
    s3, _, r3 = score_ioc("url", "http://1.2.3.4/x", "")
    assert any("ip-in-url" in r for r in r3)
    s4, _, r4 = score_ioc("domain", "kqjx9zq7vwm4bd8splnx0q.com", "")
    assert any("dga" in r for r in r4)
    s5, lvl5, _ = score_ioc("ip", "8.8.8.8", "")
    assert lvl5.lower() == "low" and s5 == 20
    assert M.MITRE_VERSION.startswith("v19")
